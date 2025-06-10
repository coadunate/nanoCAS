import json
import logging
import os
import shutil
import subprocess
import sys
import time
import glob
import pysam
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
        # Load previously processed files
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                self.processed_files = set(f.read().splitlines())
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            self.config = json.load(f)
        self.file_type = self.config.get('fileType', 'FASTQ')
        if not os.path.exists(self.coverage_file):
            with open(self.coverage_file, 'w') as f:
                f.write("timestamp,reference,fold_coverage,read_count\n")

    def on_moved(self, event):
        self.on_any_event(event)

    def on_any_event(self, event):
        src_path = event.src_path
        if src_path in self.processed_files:
            logger.debug(f"Skipping already processed file: {src_path}")
            return
        if not self.wait_for_file_stability(src_path):
            logger.error(f"File {src_path} is not stable, skipping.")
            return
        if self.file_type == 'FASTQ' and src_path.endswith((".fastq", ".fasta", ".fastq.gz", ".fq.gz")):
            logger.debug(f'Processing FASTQ file: {src_path}')
            self.process_fastq_file(src_path)
        elif self.file_type == 'BAM' and src_path.endswith(".bam"):
            logger.debug(f'Processing BAM file: {src_path}')
            self.process_bam_file(src_path)
        else:
            logger.debug(f"Ignoring file {src_path} as it does not match expected type {self.file_type}")
        # Mark file as processed
        self.processed_files.add(src_path)
        with open(self.processed_files_path, 'a') as f:
            f.write(src_path + '\n')

    def wait_for_file_stability(self, file_path, timeout=60, interval=1):
        """Ensure file is fully written by checking size stability."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                size1 = os.path.getsize(file_path)
                time.sleep(interval)
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

    def process_fastq_file(self, src_path: str):
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
        self.calculate_and_record_coverage()
        # Clean up
        if os.path.exists(sorted_bam_output):
            os.remove(sorted_bam_output)

    def process_bam_file(self, bam_path: str):
        """Process BAM file by merging and calculating coverage."""
        if not self.is_bam_valid(bam_path):
            logger.error(f"Skipping invalid BAM file: {bam_path}")
            return
        self.merge_bam(bam_path)
        self.calculate_and_record_coverage()

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

    def calculate_and_record_coverage(self):
        """Calculate and record fold coverage (average depth) and read count per reference."""
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
                # Sum depths across all bases (A, C, G, T) at each position
                total_depth = sum(sum(cov) for cov in coverage)
                # Calculate fold coverage as total depth divided by reference length
                fold_coverage = total_depth / ref_length if ref_length > 0 else 0
                read_count = bam.count(ref)  # Count reads mapping to this reference
                coverage_data[ref] = {"fold_coverage": fold_coverage, "read_count": read_count}
                print(f"Reference: {ref}, Fold Coverage: {fold_coverage:.2f}x, Read Count: {read_count}")
                # Update alert check to use fold coverage if needed
                self.check_fold_coverage_alert(ref, fold_coverage)
            bam.close()

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            with open(self.coverage_file, 'a') as f:
                for ref, cov in coverage_data.items():
                    f.write(f"{timestamp},{ref},{cov['fold_coverage']},{cov['read_count']}\n")
            logger.debug(f"Coverage and read counts recorded at {timestamp}")

            # Emit coverage update via Socket.IO
            socketio.emit('coverage_update', {
                'projectId': self.config.get('projectId', ''),
                'timestamp': timestamp,
                'coverage': coverage_data
            })
        except Exception as e:
            logger.error(f"Error calculating coverage: {e}")

    def check_fold_coverage_alert(self, ref: str, fold_coverage: float):
        """Check if fold coverage exceeds threshold and send alerts."""
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            alertinfo_cfg_data = json.load(f)
        queries = alertinfo_cfg_data.get("queries", [])
        device = alertinfo_cfg_data.get("device", "")
        for query in queries:
            if ref == query.get("header", ""):
                threshold = float(query.get("threshold", 0))
                if fold_coverage >= threshold:
                    alert_str = f"Alert: {query['name']} fold coverage reached {fold_coverage:.2f}x (threshold: {threshold}x)"
                    logger.critical(alert_str)
                    if device:
                        LinuxNotification.send_notification(device, alert_str)
                    if "alertNotifConfig" in alertinfo_cfg_data:
                        email_config = alertinfo_cfg_data['alertNotifConfig']
                        send_email("nanoCAS Alert", alert_str, email_config)
                    if os.getenv('TWILIO_ACCOUNT_SID'):
                        send_sms(alert_str)
