import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import glob
import pysam
import numpy as np
from threading import Lock
from watchdog.events import FileSystemEventHandler
from app import socketio
from .LinuxNotification import LinuxNotification
from .email import send_email
from .sms import send_sms

# Set up logging
logger = logging.getLogger('nanocas')

class FileHandler(FileSystemEventHandler):
    def __init__(self, app_loc: str):
        """
        Initialize the FileHandler with the application location.
        Sets up paths for merged BAM files, coverage data, and processed files.
        """
        self.app_loc = app_loc
        self.num_files_classified = 0
        self.merged_bam = os.path.join(self.app_loc, 'merged.bam')
        self.stable_bam = os.path.join(self.app_loc, 'merged_stable.bam')  # Stable copy for reading
        self.coverage_file = os.path.join(self.app_loc, 'coverage.csv')
        self.processed_files_path = os.path.join(self.app_loc, 'processed_files.txt')
        self.processed_files = set()
        self.processed_files_lock = Lock()  # Lock for thread-safe access to processed files
        # Track sent alerts to avoid duplicate notifications
        self.sent_alerts_path = os.path.join(self.app_loc, 'sent_alerts.json')
        self.sent_alerts_lock = Lock()
        self.sent_alerts = self._load_sent_alerts()
        
        # Load previously processed files if the file exists
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                self.processed_files = set(f.read().splitlines())
        
        # Load configuration from alertinfo.cfg
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            self.config = json.load(f)
        self.file_type = self.config.get('fileType', 'FASTQ')
        self.header_to_query = {}
        for query in self.config.get("queries", []):
            headers = []
            if "headers" in query and query["headers"]:
                headers.extend(query["headers"])
            if "header" in query and query["header"]:
                headers.append(query["header"])
            for h in headers:
                self.header_to_query[h] = query

        # Load regions data
        self.regions_json_path = os.path.join(self.app_loc, 'regions.json')
        self.regions_data = {}
        if os.path.exists(self.regions_json_path):
            with open(self.regions_json_path, 'r') as f:
                self.regions_data = json.load(f)

    def _load_sent_alerts(self):
        """Load previously sent alerts from JSON file."""
        if os.path.exists(self.sent_alerts_path):
            try:
                with open(self.sent_alerts_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Could not load sent alerts file, starting fresh")
        return {}

    def _save_sent_alerts(self):
        """Save sent alerts to JSON file."""
        with self.sent_alerts_lock:
            with open(self.sent_alerts_path, 'w') as f:
                json.dump(self.sent_alerts, f, indent=2)

    def _check_if_alert_sent(self, alert_key: str) -> bool:
        """Check if an alert has already been sent for this key."""
        with self.sent_alerts_lock:
            return alert_key in self.sent_alerts

    def _mark_alert_as_sent(self, alert_key: str, alert_info: dict):
        """Mark an alert as sent with timestamp and details."""
        with self.sent_alerts_lock:
            self.sent_alerts[alert_key] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'info': alert_info
            }
            self._save_sent_alerts()

    def on_moved(self, event):
        """Handle file move events by processing the new file path."""
        self.on_any_event(event)

    def on_any_event(self, event):
        """Handle any file system event (e.g., new file created or moved)."""
        src_path = event.src_path
        with self.processed_files_lock:
            if src_path in self.processed_files:
                logger.debug(f"Skipping already processed file: {src_path}")
                return
        if not self.wait_for_file_stability(src_path):
            logger.error(f"File {src_path} is not stable, skipping.")
            return
        mtime = os.path.getctime(src_path)
        timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        if self.file_type == 'FASTQ' and src_path.endswith((".fastq", ".fasta", ".fastq.gz", ".fq.gz")):
            logger.debug(f'Processing FASTQ file: {src_path} with timestamp {timestamp}')
            self.process_fastq_file(src_path, timestamp)
        elif self.file_type == 'BAM' and src_path.endswith(".bam"):
            logger.debug(f'Processing BAM file: {src_path} with timestamp {timestamp}')
            self.process_bam_file(src_path, timestamp)
        else:
            logger.debug(f"Ignoring file {src_path} as it does not match expected type {self.file_type}")
        # Mark file as processed
        with self.processed_files_lock:
            self.processed_files.add(src_path)
            with open(self.processed_files_path, 'a') as f:
                f.write(src_path + '\n')

    def wait_for_file_stability(self, file_path, timeout=60, interval=1):
        """Ensure the file is fully written by checking if its size stabilizes."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                logger.error(f"File {file_path} no longer exists.")
                return False
            try:
                size1 = os.path.getsize(file_path)
                time.sleep(interval)
                if not os.path.exists(file_path):
                    logger.error(f"File {file_path} no longer exists.")
                    return False
                size2 = os.path.getsize(file_path)
                if size1 == size2:
                    return True
            except OSError as e:
                logger.error(f"Error checking file size for {file_path}: {e}")
                return False
        logger.warning(f"File {file_path} did not stabilize within {timeout} seconds.")
        return False

    def is_bam_valid(self, bam_file):
        """Check if a BAM file is valid using pysam quickcheck."""
        try:
            pysam.quickcheck(bam_file)
            return True
        except pysam.utils.SamtoolsError as e:
            logger.error(f"BAM file {bam_file} is invalid or corrupted: {e}")
            return False

    def process_fastq_file(self, src_path: str, timestamp: str = None):
        """
        Process a FASTQ file by aligning it to the database and merging the results.
        """
        index_file = self.get_index_file()
        if not index_file:
            return

        # Generate sorted BAM directly with minimap2
        sorted_bam_output = os.path.join(self.app_loc, 'minimap2', 'runs', f'{os.path.basename(src_path)}_sorted.bam')
        cmd = f'minimap2 -a {index_file} {src_path} | samtools view -b | samtools sort -o {sorted_bam_output}'
        try:
            logger.debug(f"Running command: {cmd}")
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error aligning FASTQ file {src_path}: {e.stderr.decode()}")
            return

        if not self.is_bam_valid(sorted_bam_output):
            logger.error(f"Generated BAM file {sorted_bam_output} is invalid.")
            if os.path.exists(sorted_bam_output):
                os.remove(sorted_bam_output)
            return

        # Merge and calculate coverage
        self.merge_bam(sorted_bam_output)
        self.calculate_and_record_coverage(timestamp)
        # Clean up
        if os.path.exists(sorted_bam_output):
            os.remove(sorted_bam_output)

    def process_bam_file(self, bam_path: str, timestamp: str = None):
        """Process a BAM file by merging it and calculating coverage."""
        if not self.is_bam_valid(bam_path):
            logger.error(f"Skipping invalid BAM file: {bam_path}")
            return
        self.merge_bam(bam_path)
        self.calculate_and_record_coverage(timestamp)

    def get_index_file(self) -> str | None:
        """Retrieve the database index file (.mmi)."""
        files = glob.glob(os.path.join(self.app_loc, 'database', '*.mmi'))
        if not files:
            logger.error("No MMI files found in database location")
            return None
        return files[0]

    def merge_bam(self, new_bam: str):
        """Merge a new BAM file with the existing merged BAM, sort it, index it, and update both merged and stable copies."""
        temp_merged = os.path.join(self.app_loc, 'temp_merged.bam')
        sorted_merged = os.path.join(self.app_loc, 'merged_sorted.bam')
        sorted_merged_index = sorted_merged + '.bai'

        # If no merged BAM exists yet, start with the new BAM
        if not os.path.exists(self.merged_bam):
            shutil.copy(new_bam, self.merged_bam)
            shutil.copy(new_bam, temp_merged)
        else:
            # Merge the existing BAM with the new one
            try:
                subprocess.run(['samtools', 'merge', temp_merged, self.merged_bam, new_bam], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error merging BAM files: {e}")
                return

        # Sort the merged BAM file
        try:
            subprocess.run(['samtools', 'sort', temp_merged, '-o', sorted_merged], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error sorting merged BAM: {e}")
            if os.path.exists(temp_merged):
                os.remove(temp_merged)
            return

        # Create an index for the sorted BAM file
        try:
            subprocess.run(['samtools', 'index', sorted_merged], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error indexing sorted BAM: {e}")
            if os.path.exists(temp_merged):
                os.remove(temp_merged)
            if os.path.exists(sorted_merged):
                os.remove(sorted_merged)
            return

        # Update both merged.bam and stable_bam atomically
        try:
            # First, update merged.bam as the cumulative file
            shutil.move(sorted_merged, self.merged_bam)
            # Then, copy to stable_bam for coverage calculation
            shutil.copy(self.merged_bam, self.stable_bam)
            if os.path.exists(sorted_merged_index):
                shutil.move(sorted_merged_index, self.merged_bam + '.bai')
                shutil.copy(self.merged_bam + '.bai', self.stable_bam + '.bai')
            else:
                logger.warning(f"Index file {sorted_merged_index} not found after indexing.")
                # Regenerate indices for both files
                subprocess.run(['samtools', 'index', self.merged_bam], check=True)
                subprocess.run(['samtools', 'index', self.stable_bam], check=True)
        except Exception as e:
            logger.error(f"Error updating BAM files or indices: {e}")
            return

        # Clean up temporary files
        if os.path.exists(temp_merged):
            os.remove(temp_merged)

    def calculate_and_record_coverage(self, timestamp: str = None):
        """Calculate and record coverage using the stable BAM file."""
        if timestamp is None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        try:
            bam = pysam.AlignmentFile(self.stable_bam, "rb", check_sq=False)
            if not bam.has_index():
                logger.error(f"Index missing for {self.stable_bam}")
                return
            coverage_data = {}
            for ref in bam.references:
                ref_length = bam.lengths[bam.references.index(ref)]
                coverage = bam.count_coverage(ref)
                total_depth_per_position = np.sum([np.array(cov) for cov in coverage], axis=0)
                total_depth = np.sum(total_depth_per_position)
                depth_coverage = total_depth / ref_length if ref_length > 0 else 0
                covered_positions = np.sum(total_depth_per_position >= 1)
                breadth_coverage = (covered_positions / ref_length) * 100 if ref_length > 0 else 0
                read_count = bam.count(ref)
                coverage_data[ref] = {
                    "depth": depth_coverage,
                    "breadth": breadth_coverage,
                    "read_count": read_count
                }
                print(f"Reference: {ref}, Depth Coverage: {depth_coverage:.2f}x, Breadth Coverage: {breadth_coverage:.2f}%, Read Count: {read_count}")
                self.check_coverage_alerts(ref, depth_coverage, breadth_coverage)

                # Region-specific coverage and alerts
                if ref in self.regions_data:
                    for region in self.regions_data[ref]:
                        if region.get('alert_enabled', False):
                            start = region['start']
                            end = region['end']
                            region_coverage = bam.count_coverage(ref, start - 1, end)
                            region_depth_per_position = np.sum([np.array(cov) for cov in region_coverage], axis=0)
                            region_total_depth = np.sum(region_depth_per_position)
                            region_length = end - start + 1
                            region_depth_coverage = region_total_depth / region_length if region_length > 0 else 0
                            region_covered_positions = np.sum(region_depth_per_position >= 1)
                            region_breadth_coverage = (region_covered_positions / region_length) * 100 if region_length > 0 else 0

                            query = self.header_to_query.get(ref)
                            threshold = float(query.get("threshold", 0)) if query else 0
                            if region_depth_coverage >= threshold:
                                alert_str = f"Alert: Region {region['id']} in {ref} depth coverage reached {region_depth_coverage:.2f}x (threshold: {threshold}x)"
                                logger.critical(alert_str)
                                self._send_notifications(alert_str)

            unmapped_count = bam.unmapped
            coverage_data['unmapped'] = {
                "depth": 0.0,
                "breadth": 0.0,
                "read_count": unmapped_count
            }

            bam.close()

            with open(self.coverage_file, 'a') as f:
                for ref, cov in coverage_data.items():
                    f.write(f"{timestamp},{ref},{cov['depth']},{cov['breadth']},{cov['read_count']}\n")
            logger.debug(f"Coverage and read counts recorded at {timestamp}")

            socketio.emit('coverage_update', {
                'projectId': self.config.get('projectId', ''),
                'timestamp': timestamp,
                'coverage': coverage_data
            })
        except Exception as e:
            logger.error(f"Error calculating coverage: {e}")

    def check_coverage_alerts(self, ref: str, depth_coverage: float, breadth_coverage: float):
        """Check if depth coverage exceeds the threshold and trigger alerts if necessary."""
        logger.debug(f"Checking alerts for {ref}: Depth {depth_coverage}, Breadth {breadth_coverage}")
        query = self.header_to_query.get(ref)
        logger.debug(f"header_to_query keys: {list(self.header_to_query.keys())}")
        logger.debug(query)
        if query:
            if query.get("alert_on_depth", False):
                depth_threshold = float(query.get("depth_threshold", 0))
                if depth_coverage >= depth_threshold:
                    alert_key = f"{ref}_depth"
                    if not self._check_if_alert_sent(alert_key):
                        alert_str = f"Alert: {query['name']} - {ref} depth coverage reached {depth_coverage:.2f}x (threshold: {depth_threshold}x)"
                        logger.critical(alert_str)
                        self._send_notifications(alert_str)
                        self._mark_alert_as_sent(alert_key, {
                            'type': 'depth',
                            'reference': ref,
                            'value': depth_coverage,
                            'threshold': depth_threshold
                        })
                    else:
                        logger.debug(f"Depth alert for {alert_key} already sent, skipping")
            if query.get("alert_on_breadth", False):
                breadth_threshold = float(query.get("breadth_threshold", 0))
                if breadth_coverage >= breadth_threshold:
                    alert_key = f"{ref}_breadth"
                    if not self._check_if_alert_sent(alert_key):
                        alert_str = f"Alert: {query['name']} - {ref} breadth coverage reached {breadth_coverage:.2f}% (threshold: {breadth_threshold}%)"
                        logger.critical(alert_str)
                        self._send_notifications(alert_str)
                        self._mark_alert_as_sent(alert_key, {
                            'type': 'breadth',
                            'reference': ref,
                            'value': breadth_coverage,
                            'threshold': breadth_threshold
                        })
                    else:
                        logger.debug(f"Breadth alert for {alert_key} already sent, skipping")
            

    def _send_notifications(self, alert_str: str):
        device = self.config.get("device", "")
        alert_notif_config = self.config.get("alertNotifConfig", {})
        if device:
            LinuxNotification.send_notification(device, alert_str)
        if alert_notif_config.get("enableEmail", False):
            email_config = alert_notif_config.get("emailConfig", {})
            if all(key in email_config for key in ["sender", "recipient", "smtpServer", "smtpPort", "password"]):
                send_email("nanoCAS Alert", alert_str, email_config)
            else:
                logger.error("Email configuration is incomplete.")
        if alert_notif_config.get("enableSMS", False):
            sms_recipient = alert_notif_config.get("smsRecipient", "")
            if sms_recipient:
                send_sms(alert_str, sms_recipient)
            else:
                logger.error("SMS recipient phone number is missing.")
    
    def get_existing_files(self, directory):
        """Get list of existing files of the specified type, sorted by modification time."""
        if self.file_type == 'FASTQ':
            extensions = ('.fastq', '.fasta', '.fastq.gz', '.fq.gz')
        elif self.file_type == 'BAM':
            extensions = ('.bam',)
        else:
            return []

        files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extensions)]
        with self.processed_files_lock:
            files = [f for f in files if f not in self.processed_files]
        files.sort(key=lambda x: os.path.getctime(x))
        return files

    def process_existing_files(self, directory):
        """Process existing files in the directory before starting the observer."""
        files = self.get_existing_files(directory)
        for file in files:
            mtime = os.path.getmtime(file)
            timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            if self.file_type == 'FASTQ':
                self.process_fastq_file(file, timestamp)
            elif self.file_type == 'BAM':
                self.process_bam_file(file, timestamp)
            with self.processed_files_lock:
                self.processed_files.add(file)
                with open(self.processed_files_path, 'a') as f:
                    f.write(file + '\n')
