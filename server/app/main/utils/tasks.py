import os
from celery import Celery
import subprocess, os, shutil, datetime
import json, sys
import logging

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
    """Download and build a database from query sequences using Minimap2."""
    # Extract task parameters
    minion = db_data['minion']
    project_id = db_data['projectId']
    device = db_data['device']
    database_dir = os.path.join(nanocas_location, 'database')
    os.makedirs(database_dir, exist_ok=True)

    # Generate unique base name from timestamp
    now = datetime.datetime.now()
    base_name = f"{now.year}{now.month:02d}{now.day:02d}{now.hour:02d}{now.minute:02d}{now.second:02d}"
    input_sequences_path = os.path.join(database_dir, f"{base_name}.fa")
    db_index_path = os.path.join(database_dir, f"{base_name}.mmi")

    # Process queries if provided
    if len(queries) > 0:
        alertinfo_cfg_path = os.path.join(nanocas_location, 'alertinfo.cfg')
        with open(alertinfo_cfg_path, 'r') as f:
            alertinfo_cfg = json.load(f)

        for i, query in enumerate(queries):
            # Extract FASTA header
            with open(query['file'], 'r', encoding='utf-8') as qf:
                for line in qf:
                    if line.startswith('>'):
                        header = line[1:].strip()
                        break
                else:
                    header = ""  # Default if no header found

            # Update alertinfo configuration in memory
            alertinfo_cfg["queries"][i]["header"] = header

            # Append query sequence to input file
            with open(query['file'], 'rb') as qf, open(input_sequences_path, 'ab') as isf:
                shutil.copyfileobj(qf, isf)
            logger.debug(f"Merged {query['file']} into {input_sequences_path}")

            # Update task progress
            percent_done = int((i + 1) / len(queries) * 50)
            self.update_state(
                state="PROGRESS",
                meta={
                    'percent-done': percent_done,
                    'message': f"Processed query {i+1}/{len(queries)}",
                    'project_id': project_id
                }
            )
            logger.debug(f"Progress: {percent_done}% done for project {project_id}")

        # Set device and save alertinfo configuration
        alertinfo_cfg['device'] = device
        with open(alertinfo_cfg_path, 'w') as f:
            json.dump(alertinfo_cfg, f)
    else:
        # Create an empty input file if no queries are provided
        with open(input_sequences_path, 'wb') as f:
            pass
        logger.debug("No queries provided, created empty input file.")

    # Build the database index
    self.update_state(
        state="PROGRESS",
        meta={'percent-done': 98, 'message': "Building the index.", 'project_id': project_id}
    )
    logger.debug("Building the index with Minimap2")
    index_cmd = f"minimap2 -x map-ont -d {db_index_path} {input_sequences_path}"
    build_log_path = os.path.join(database_dir, 'building_index.txt')
    with open(build_log_path, 'w') as f:
        try:
            subprocess.run(index_cmd, shell=True, check=True, stdout=f, stderr=f)
        except subprocess.CalledProcessError as e:
            logger.error(f"Minimap2 failed: {e}")
            return "ER1"
        
    # Create coverage.csv with header as soon as MMI file is generated
    coverage_file = os.path.join(nanocas_location, 'coverage.csv')
    with open(coverage_file, 'w') as f:
        f.write("timestamp,reference,depth,breadth,read_count\n")

    # Mark task as complete
    self.update_state(
        state="PROGRESS",
        meta={
            'percent-done': 100,
            'message': "Database successfully downloaded and built.",
            'nanocas_location': nanocas_location,
            'minion': minion,
            'device': device,
            'project_id': project_id
        }
    )
    logger.debug("Database build completed successfully")
    return {"minion": minion, "nanocas_location": nanocas_location, "device": device}