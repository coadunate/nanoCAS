from flask import url_for, session
from flask_socketio import emit, send
from .. import socketio

from threading import Thread, Event

# for download_database
import os, shutil, subprocess
from time import sleep

# for run_fastq_watcher
from .utils.FileHandler import FileHandler
from .utils.tasks import int_download_database
from .utils import LinuxNotification

# for run_fasq_watcher
from watchdog.observers import Observer

import json

# for Logger
import logging

logger = logging.getLogger('nanocas')

# Global dictionary to store observers by project ID
observers = {}


# HELPER FUNCTIONS

def run_fastq_watcher(app_loc, minion_loc):
    logger.debug(f"Starting file watcher on {app_loc}")
    event_handler = FileHandler(app_loc)
    observer = Observer()
    observer.schedule(event_handler, path=minion_loc, recursive=False)
    observer.start()
    try:
        while True:
            sleep(1)
    except:
        observer.stop()


@socketio.on('connect', namespace="/analysis")
def analysis_connected():
    logger.debug("Debug: Unused analysis connection made.")


@socketio.on('disconnect', namespace="/analysis")
def analysis_disconnected():
    # delete the analysis_busy file
    subprocess.call(['rm', session.get('nanocas_location') + 'analysis_busy'])
    logger.debug("Debug: Disconnect from analysis connection.")


@socketio.on('remove_analysis')
def remove_analysis(data):
    project_id = data['projectId']
    # Path where analysis data is stored
    nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/', project_id)

    if os.path.exists(nanocas_location):
        # Delete the analysis directory
        shutil.rmtree(nanocas_location)

        # Update a cache file (if applicable)
        cache_path = os.path.join(os.path.expanduser('~'), '.nanocas/.cache')
        if os.path.exists(cache_path):
            with open(cache_path, 'r+') as cache_fs:
                lines = cache_fs.readlines()
                cache_fs.seek(0)
                for line in lines:
                    if project_id not in line:
                        cache_fs.write(line)
                cache_fs.truncate()

        # Notify the client of success
        emit('analysis_removed', {'success': True, 'message': 'Analysis removed successfully'})
    else:
        # Notify the client of failure
        emit('analysis_removed', {'success': False, 'message': 'Analysis not found'})

@socketio.on('start_fastq_file_listener')
def start_fastq_file_listener(data):
    project_id = data['projectId']
    nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/' + project_id + '/')
    minion_location = data['minion_location']

    if project_id not in observers:
        try:
            event_handler = FileHandler(nanocas_location)
            observer = Observer()
            observer.schedule(event_handler, path=minion_location, recursive=False)
            observer.start()
            observers[project_id] = observer
            emit('fastq_file_listener_started', {'projectId': project_id})
            logger.debug(f"Started file listener for project {project_id}")
        except Exception as e:
            emit('fastq_file_listener_error', {'projectId': project_id, 'error': str(e)})
            logger.error(f"Error starting file listener for project {project_id}: {e}")
    else:
        emit('fastq_file_listener_already_running', {'projectId': project_id})
        logger.debug(f"File listener already running for project {project_id}")

@socketio.on('stop_fastq_file_listener')
def stop_fastq_file_listener(data):
    project_id = data['projectId']
    if project_id in observers:
        try:
            observer = observers[project_id]
            observer.stop()
            observer.join()
            del observers[project_id]
            emit('fastq_file_listener_stopped', {'projectId': project_id})
            logger.debug(f"Stopped file listener for project {project_id}")
        except Exception as e:
            emit('fastq_file_listener_error', {'projectId': project_id, 'error': str(e)})
            logger.error(f"Error stopping file listener for project {project_id}: {e}")
    else:
        emit('fastq_file_listener_not_running', {'projectId': project_id})
        logger.debug(f"No file listener running for project {project_id}")

@socketio.on('check_fastq_file_listener')
def check_fastq_file_listener(data):
    project_id = data['projectId']
    is_running = project_id in observers
    emit('fastq_file_listener_status', {'projectId': project_id, 'is_running': is_running})

def on_raw_message(message):
    status = message['status']
    if status == "PROGRESS":

        percent_done = message['result']['percent-done']
        status_message = message['result']['message']
        project_id = message['result']['project_id']

        emit(
            'download_database_status',
            {'percent_done': percent_done, 'status_message': status_message}
        )

        if percent_done == 100:
            minion = message['result']['minion']
            nanocas_location = message['result']['nanocas_location']

            logger.debug("Debug: Starting the MinION Listener")
            # start_fastq_file_listener(nanocas_location, minion)

    if status == "SUCCESS":
        minion = message['result']['minion']
        nanocas_location = message['result']['nanocas_location']
        logger.debug(f"Debug: MinION Location: {minion}, nanocas Location: {nanocas_location}")


@socketio.on('download_database', namespace="/")
def download_database(dbinfo):
    project_id = dbinfo["projectId"]
    device = dbinfo.get("device", "")
    alert_notif_config = dbinfo.get("alertNotifConfig", {})
    file_type = dbinfo.get("fileType", "FASTQ")  # Add fileType
    nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/' + project_id + '/')

    if not os.path.exists(nanocas_location):
        os.makedirs(nanocas_location)
    else:
        shutil.rmtree(nanocas_location)
        os.makedirs(nanocas_location)

    queries = dbinfo["queries"]
    dbinfo["fileType"] = file_type  # Ensure fileType is included
    with open(nanocas_location + 'alertinfo.cfg', 'w+') as alert_config_file:
        alert_config_file.write(json.dumps(dbinfo))

    # Send notification only if device is specified and not empty
    if device:
        alert_str = f"You can find the nanocas alert page for {project_id} at http://localhost:3000/analysis/{project_id}"
        LinuxNotification.send_notification(device, alert_str, severity=1)

    # Rest of the function remains unchanged
    os.umask(0)
    os.makedirs(os.path.join(nanocas_location, 'database'), mode=0o777, exist_ok=True)
    os.umask(0)
    os.makedirs(nanocas_location + 'minimap2/runs', mode=0o777, exist_ok=True)
    res = int_download_database.apply_async(args=[dbinfo, nanocas_location, queries])
    res.get(on_message=on_raw_message, propagate=False)
    
    
    
   


# LOGGER HOOKS
@socketio.on('log')
def log(msg, lvl):
    if str(lvl).upper() == "INFO":
        logger.info(msg)
    elif str(lvl).upper() == "DEBUG":
        logger.debug(msg)
    elif str(lvl).upper() == "WARNING":
        logger.warning(msg)
    elif str(lvl).upper() == "ERROR":
        logger.error(msg)
    elif str(lvl).upper() == "CRITICAL":
        logger.critical(msg)
