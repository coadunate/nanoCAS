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
from .LinuxNotification import LinuxNotification

logger = logging.getLogger('micas')

class FileHandler(FileSystemEventHandler):
    def __init__(self, app_loc: str):
        self.app_loc = app_loc
        self.num_files_classified = 0
        self.merged_bam = os.path.join(self.app_loc, 'merged.bam')
        self.coverage_file = os.path.join(self.app_loc, 'coverage.csv')
        # Load configuration to get expected file type
        with open(os.path.join(self.app_loc, 'alertinfo.cfg'), 'r') as f:
            self.config = json.load(f)
        self.file_type = self.config.get('fileType', 'FASTQ')  # Default to FASTQ if not specified
        # Initialize coverage file with headers if it doesn’t exist
        if not os.path.exists(self.coverage_file):
            with open(self.coverage_file, 'w') as f:
                f.write("timestamp,reference,coverage\n")

    def on_moved(self, event):
        self.on_any_event(event)

    def on_any_event(self, event):
        src_path = event.src_path
        if not self.wait_for_file_stability(src_path):
            logger.error(f"File {src_path} is not stable, skipping.")
            return
        if self.file_type == 'FASTQ' and src_path.endswith((".fastq", ".fasta")):
            logger.debug(f'Processing FASTQ file: {src_path}')
            self.process_fastq_file(src_path)
        elif self.file_type == 'BAM' and src_path.endswith(".bam"):
            logger.debug(f'Processing BAM file: {src_path}')
            self.process_bam_file(src_path)
        else:
            logger.debug(f"Ignoring file {src_path} as it does not match expected type {self.file_type}")

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
        # Process for alerts
        self.process_minimap2_for_alerts(src_path, index_file)
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
        """Calculate and record average coverage per reference."""
        try:
            bam = pysam.AlignmentFile(self.merged_bam, "rb", check_sq=False)
            if not bam.has_index():
                logger.error(f"Index missing for {self.merged_bam}")
                return
            coverage_data = {}
            for ref in bam.references:
                pileup = bam.pileup(ref)
                depths = [p.nsegments for p in pileup if p.nsegments > 0]  # Count of reads at each position
                avg_coverage = sum(depths) / len(depths) if depths else 0
                coverage_data[ref] = avg_coverage
            bam.close()

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            with open(self.coverage_file, 'a') as f:
                for ref, cov in coverage_data.items():
                    f.write(f"{timestamp},{ref},{cov}\n")
            logger.debug(f"Coverage recorded at {timestamp}")
        except Exception as e:
            logger.error(f"Error calculating coverage: {e}")

    def process_minimap2_for_alerts(self, src_path: str, index_file: str):
        """Process FASTQ for alerts using PAF output."""
        paf_output = os.path.join(self.app_loc, 'minimap2', 'runs', f'{os.path.basename(src_path)}.paf')
        cmd = f'minimap2 {index_file} {src_path} -o {paf_output}'
        subprocess.run(cmd, shell=True)
        self.process_minimap2_output(paf_output)
        if os.path.exists(paf_output):
            os.remove(paf_output)

    def process_minimap2_output(self, minimap2_output: str):
        """Process PAF output for alerts."""
        final_output = os.path.join(self.app_loc, 'minimap2', 'final.out.paf')
        with open(minimap2_output, 'r') as f:
            line = f.readline().strip()
            if not line:
                logger.error(f"PAF file {minimap2_output} is empty")
                return
            fields = line.split("\t")
            if len(fields) < 10:
                logger.error(f"Unexpected format in {minimap2_output}")
                return
            match_alert_header = fields[5]
            num_match = int(fields[9])
            tot_len = int(fields[6])
            percent_match_value = (num_match / tot_len) * 100
            logger.debug(f"Alignment: Header={match_alert_header}, % Match={percent_match_value:.2f}")
            self.update_alert_info(match_alert_header, percent_match_value)
            self.handle_output_files(minimap2_output, final_output)

    def update_alert_info(self, match_alert_header: str, percent_match_value: float):
        """Update alert info and send notifications if threshold exceeded."""
        alertinfo_cfg_file = os.path.join(self.app_loc, 'alertinfo.cfg')
        try:
            with open(alertinfo_cfg_file, 'r') as f:
                alertinfo_cfg_data = json.load(f)
            queries = alertinfo_cfg_data.get("queries", [])
            device = alertinfo_cfg_data.get("device", "")
            for query in queries:
                if match_alert_header == query.get("header", ""):
                    query["current_value"] = percent_match_value
                    threshold = float(query.get("threshold", 0))
                    if percent_match_value >= threshold:
                        alert_str = f"Alert: {query['name']} detected at {percent_match_value:.2f}% (threshold: {threshold}%)"
                        logger.critical(alert_str)
                        if device:
                            LinuxNotification.send_notification(device, alert_str)
            with open(alertinfo_cfg_file, 'w') as f:
                json.dump(alertinfo_cfg_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error updating alert info: {e}")

    def handle_output_files(self, minimap2_output: str, final_output: str):
        """Manage PAF output files."""
        if os.path.isfile(final_output):
            with open(final_output, "a+") as f:
                f.writelines(open(minimap2_output).readlines())
        else:
            os.rename(minimap2_output, final_output)
        self.num_files_classified += 1