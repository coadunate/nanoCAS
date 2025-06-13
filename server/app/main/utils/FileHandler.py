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

logger = logging.getLogger('nanocas')

class FileHandler(FileSystemEventHandler):
    def __init__(self, app_loc: str):
        self.app_loc = app_loc
        self.num_files_classified = 0
        self.merged_bam = os.path.join(self.app_loc, 'merged.bam')
        self.coverage_file = os.path.join(self.app_loc, 'coverage.csv')
        self.processed_files_path = os.path.join(self.app_loc, 'processed_files.txt')
        self.processed_files = set()
        self.processed_files_lock = Lock()  # Add lock for thread safety
        # Load previously processed files
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                self.processed_files = set(f.read().splitlines())
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            self.config = json.load(f)
        self.file_type = self.config.get('fileType', 'FASTQ')

    def on_moved(self, event):
        self.on_any_event(event)

    def on_any_event(self, event):
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
        """Ensure file is fully written by checking size stability."""
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
        """Check if a BAM file is valid."""
        try:
            pysam.quickcheck(bam_file)
            return True
        except pysam.utils.SamtoolsError as e:
            logger.error(f"BAM file {bam_file} is invalid or corrupted: {e}")
            return False

    def process_fastq_file(self, src_path: str, timestamp: str = None):
        """Process FASTQ file by aligning to database and calculating coverage."""
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
        """Process BAM file by merging and calculating coverage."""
        if not self.is_bam_valid(bam_path):
            logger.error(f"Skipping invalid BAM file: {bam_path}")
            return
        self.merge_bam(bam_path)
        self.calculate_and_record_coverage(timestamp)

    def get_index_file(self) -> str | None:
        """Retrieve the database index file."""
        files = glob.glob(os.path.join(self.app_loc, 'database', '*.mmi'))
        if not files:
            logger.error("No MMI files found in database location")
            return None
        return files[0]

    def merge_bam(self, new_bam: str):
        """Merge new BAM with existing merged BAM, ensuring sorted output."""
        if not os.path.exists(self.merged_bam):
            shutil.copy(new_bam, self.merged_bam)
        else:
            temp_merged = os.path.join(self.app_loc, 'temp_merged.bam')
            try:
                subprocess.run(['samtools', 'merge', temp_merged, self.merged_bam, new_bam], check=True)
                shutil.move(temp_merged, self.merged_bam)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error merging BAM files: {e}")
                return
        # Sort and index the merged BAM
        try:
            sorted_merged = os.path.join(self.app_loc, 'merged_sorted.bam')
            subprocess.run(['samtools', 'sort', self.merged_bam, '-o', sorted_merged], check=True)
            shutil.move(sorted_merged, self.merged_bam)
            subprocess.run(['samtools', 'index', self.merged_bam], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error sorting/indexing merged BAM: {e}")

    def calculate_and_record_coverage(self, timestamp: str = None):
        """Calculate and record depth coverage (average depth), breadth coverage, and read count per reference."""
        if timestamp is None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        try:
            bam = pysam.AlignmentFile(self.merged_bam, "rb", check_sq=False)
            if not bam.has_index():
                logger.error(f"Index missing for {self.merged_bam}")
                return
            coverage_data = {}
            for ref in bam.references:
                ref_length = bam.lengths[bam.references.index(ref)]
                # Get coverage depth across all positions for this reference
                coverage = bam.count_coverage(ref)
                # Sum depths across all bases (A, C, G, T) at each position using NumPy
                total_depth_per_position = np.sum([np.array(cov) for cov in coverage], axis=0)
                total_depth = np.sum(total_depth_per_position)
                # Depth coverage is average depth across the reference
                depth_coverage = total_depth / ref_length if ref_length > 0 else 0
                # Breadth coverage: percentage of positions with at least one read
                covered_positions = np.sum(total_depth_per_position >= 1)
                breadth_coverage = (covered_positions / ref_length) * 100 if ref_length > 0 else 0
                read_count = bam.count(ref)  # Count reads mapping to this reference
                coverage_data[ref] = {
                    "depth": depth_coverage,
                    "breadth": breadth_coverage,
                    "read_count": read_count
                }
                print(f"Reference: {ref}, Depth Coverage: {depth_coverage:.2f}x, Breadth Coverage: {breadth_coverage:.2f}%, Read Count: {read_count}")
                # Update alert check to use depth coverage if needed
                self.check_depth_coverage_alert(ref, depth_coverage)

            # add unmapped reads
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

            # Emit coverage update via Socket.IO
            socketio.emit('coverage_update', {
                'projectId': self.config.get('projectId', ''),
                'timestamp': timestamp,
                'coverage': coverage_data
            })
        except Exception as e:
            logger.error(f"Error calculating coverage: {e}")

    def check_depth_coverage_alert(self, ref: str, depth_coverage: float):
        """Check if depth coverage exceeds threshold and send alerts."""
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            alertinfo_cfg_data = json.load(f)
        queries = alertinfo_cfg_data.get("queries", [])
        device = alertinfo_cfg_data.get("device", "")
        alert_notif_config = alertinfo_cfg_data.get("alertNotifConfig", {})
        for query in queries:
            if ref == query.get("header", ""):
                threshold = float(query.get("threshold", 0))
                if depth_coverage >= threshold:
                    alert_str = f"Alert: {query['name']} depth coverage reached {depth_coverage:.2f}x (threshold: {threshold}x)"
                    logger.critical(alert_str)
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
        # Sort by modification time
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