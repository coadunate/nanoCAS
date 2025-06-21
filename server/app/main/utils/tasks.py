import os
from celery import Celery
import subprocess, os, shutil, datetime
import json, sys
import logging
import shutil
from Bio import SeqIO

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
broker_url = f'redis://{redis_host}:{redis_port}'

# Configure the 'nanocas' logger for Celery tasks
logger = logging.getLogger('nanocas')
if not logger.handlers:  # Prevent duplicate handlers
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

celery = Celery('tasks', broker=broker_url, backend='redis')

@celery.task(bind=True, name='app.main.tasks.int_download_database')
def int_download_database(self, db_data, nanocas_location, queries):
    """
    Download and build a database from query sequences using Minimap2.

    Args:
        db_data (dict): Contains 'minion', 'projectId', and 'device'.
        nanocas_location (str): Path to the nanocas working directory.
        queries (list): List of query dicts with 'file' and 'header'.

    Returns:
        dict or str: Task result or error code.
    """
    def update_progress(percent, message):
        self.update_state(
            state="PROGRESS",
            meta={
                'percent-done': percent,
                'message': message,
                'project_id': db_data.get('projectId')
            }
        )
        logger.debug(f"Progress: {percent}% - {message}")

    minion = db_data.get('minion')
    project_id = db_data.get('projectId')
    device = db_data.get('device')
    database_dir = os.path.join(nanocas_location, 'database')
    os.makedirs(database_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    input_sequences_path = os.path.join(database_dir, f"{timestamp}.fa")
    db_index_path = os.path.join(database_dir, f"{timestamp}.mmi")
    alertinfo_cfg_path = os.path.join(nanocas_location, 'alertinfo.cfg')

    
    try:
        try:
            with open(alertinfo_cfg_path, 'r') as f:
                alertinfo_cfg = json.load(f)
                print(f"Loaded alertinfo.cfg: {alertinfo_cfg}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load alertinfo.cfg: {e}")
            return "ER_ALERTINFO"

        # Prepare to write all matching records to input_sequences_path
        try:
            with open(input_sequences_path, 'w') as out_fasta:
                for i, query in enumerate(queries):
                    header = query.get('header')
                    file_path = query.get('file')
                    logger.debug(f"Processing query {i+1}/{len(queries)}: {file_path} (header: {header})")

                    try:
                        found = False
                        for record in SeqIO.parse(file_path, "fasta"):
                            if record.id == header:
                                SeqIO.write(record, out_fasta, "fasta")
                                found = True
                                logger.debug(f"Header '{header}' found and written to {input_sequences_path}")
                                break
                        if not found:
                            logger.warning(f"Header '{header}' not found in {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to process FASTA file {file_path}: {e}")

                    update_progress(int((i + 1) / len(queries) * 50), f"Processed query {i+1}/{len(queries)}")

        except Exception as e:
            logger.error(f"Failed to write to input_sequences_path: {e}")
            return "ER_INPUTFILE"

        alertinfo_cfg['device'] = device
        try:
            with open(alertinfo_cfg_path, 'w') as f:
                json.dump(alertinfo_cfg, f)
        except Exception as e:
            logger.error(f"Failed to write alertinfo.cfg: {e}")
            return "ER_ALERTINFO_WRITE"

        # Build the database index
        update_progress(98, "Building the index.")
        index_cmd = [
            "minimap2", "-x", "map-ont", "-d", db_index_path, input_sequences_path
        ]
        build_log_path = os.path.join(database_dir, 'building_index.txt')
        try:
            with open(build_log_path, 'w') as log_file:
                subprocess.run(index_cmd, check=True, stdout=log_file, stderr=log_file)
            logger.debug("Minimap2 index built successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Minimap2 failed: {e}")
            return "ER_MINIMAP2"
        except Exception as e:
            logger.error(f"Unexpected error during Minimap2 execution: {e}")
            return "ER_MINIMAP2_UNKNOWN"

        # Create coverage.csv with header
        coverage_file = os.path.join(nanocas_location, 'coverage.csv')
        try:
            with open(coverage_file, 'w') as f:
                f.write("timestamp,reference,depth,breadth,read_count\n")
            logger.debug(f"Created coverage file at {coverage_file}")
        except Exception as e:
            logger.error(f"Failed to create coverage.csv: {e}")
            return "ER_COVERAGE"

        update_progress(100, "Database successfully downloaded and built.")

        logger.info("Database build completed successfully")
        return {
            "minion": minion,
            "nanocas_location": nanocas_location,
            "device": device,
        }
    
    finally:
        for query in queries:
            file_path = query.get('file')
            temp_dir = os.path.dirname(file_path)
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Failed to remove temporary directory {temp_dir}: {e}")