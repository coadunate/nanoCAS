import ast
import json
import logging
import os
import random
import string
import uuid
import subprocess

from flask import session, render_template, request, abort, jsonify
from . import main
from .utils import LinuxNotification

logger = logging.getLogger('nanocas')

NANOCAS_DIR = os.path.join(os.path.expanduser('~'), '.nanocas')
CACHE_PATH = os.path.join(os.path.expanduser('~'), '.nanocas/.cache') # Add to CONFIG

@main.route('/version', methods=['GET'])
def version():
    return json.dumps({"version": "v0.0.2", "name": "nanocas PoC"})

@main.route('/get_timeline_info', methods=["GET"])
def get_timeline_info():
    timeline_path = get_analysis_timeline_path()
    if os.path.exists(timeline_path):
        with open(timeline_path, 'r') as analysis_timeline:
            line = analysis_timeline.readline()
            try:
                num_total_reads, num_classified_reads = line.split("\t")
                return jsonify(status=200,
                               num_total_reads=int(num_total_reads),
                               num_classified_reads=int(num_classified_reads))
            except ValueError as e:
                logger.error(f"Error parsing timeline info: {e}")
                return jsonify({'message': 'Invalid timeline format'}), 400
    else:
        return jsonify({'message': 'Timeline info not found'}), 404

def get_nanocas_cache_path():
    return os.path.join(NANOCAS_DIR, '.cache')

def get_analysis_timeline_path():
    return os.path.join(NANOCAS_DIR, 'analysis.timeline')

def write_to_cache(uid, minION_location, uid_dir):
    entry = f"{uid}\t{minION_location}\t{uid_dir}\n"
    with open(get_nanocas_cache_path(), 'a+') as cache_fs:
        cache_fs.write(entry)

@main.route('/get_uid', methods=["POST"])
def get_uid():
    minION_location = request.form.get('minION')
    if not minION_location:
        abort(400, description="minION location not provided.")

    cache_path = get_nanocas_cache_path()
    uid = str(uuid.uuid4())

    if os.path.exists(cache_path):
        with open(cache_path, 'r') as cache_fs:
            lines = cache_fs.readlines()
            for line in lines:
                parts = line.strip().split('\t')
                if len(parts) >= 2 and parts[1] == minION_location:
                    return jsonify({'uid': parts[0]})  # Return existing UID

    uid_dir = os.path.join(NANOCAS_DIR, uid)
    write_to_cache(uid, minION_location, uid_dir)

    return jsonify({'uid': uid})

@main.route('/get_all_analyses', methods=['GET'])
def get_all_analyses():
    if request.method == "GET":
        data = []
        validate_cache()
        with open(CACHE_PATH, 'r') as cache_fs:
            for line in cache_fs:
                [projectId, minion_dir, NANOCAS_DIR] = line.split("\t")
                data.append({
                    "id"        : projectId,
                    "minion_dir": minion_dir,
                    "NANOCAS_DIR" : NANOCAS_DIR
                })

        return json.dumps({
            'status': 200,
            'data'  : data
        })

@main.route('/delete_analyses', methods=['POST'])
def delete_analyses():
    if request.method == "GET":
        return "Unexpected request method. Expected a GET request."

    # Get Post Data
    uid = request.form['uid']
    found = False
    with open(CACHE_PATH, 'r+') as cache_fs:
        filtered_lines = []
        for line in cache_fs:
            if uid not in line:
                filtered_lines.append(line)
            else:
                logger.debug(f"Debug: Removed id {uid} from cache")
                found = True
        cache_fs.seek(0)
        cache_fs.write("".join(filtered_lines))
        cache_fs.truncate()

    # delete the nanocas directory for the uid
    uid_dir = os.path.join(os.path.expanduser('~'), '.nanocas/' + uid) # Add to CONFIG
    if os.path.exists(uid_dir):
        subprocess.call(['rm', '-rf', uid_dir])
    
    return json.dumps({
        'status': 200,
        'found' : found
    })

@main.route('/get_analysis_info', methods=['GET'])
def get_analysis_info():
    if request.method == 'GET':
        uid = request.args.get('uid')

        # get minion and nanocas location
        nanocas_path = ""
        validate_cache()
        with open(CACHE_PATH, 'r') as cache_fs:
            found = False
            for line in cache_fs:
                entry = line.split("\t")
                entry_id = entry[0]
                entry_nanocas_path = entry[2].rstrip()
                if uid == entry_id:
                    nanocas_path = entry_nanocas_path
                    found = True
                    break

        if not found:
            return json.dumps({'status': 404, 'message': "Couldn't find the analysis data with UID: " + uid})
        else:

            alert_cfg_file = os.path.join(nanocas_path, 'alertinfo.cfg')
            alert_cfg_obj = json.load(open(alert_cfg_file))

            return json.dumps({
                'status': 200,
                'data'  : alert_cfg_obj
            })

    else:
        return "Unexpected request method. Expected a GET request."

@main.route('/analysis', methods=['GET'])
def analysis():
    if (request.method == 'GET'):

        nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/') # Add to CONFIG
        minion = request.args.get('minion')

        session['nanocas_location'] = nanocas_location
        session['minion'] = minion

        error = []

        # Location for the applicaiton data directory
        nanocas_location = nanocas_location if nanocas_location.endswith('/') else nanocas_location + '/'

        # check if nanocas_location is valid
        if subprocess.call(['ls', nanocas_location]) == 0:
            # if nanocas_location exists
            if subprocess.call(['ls', nanocas_location + 'alertinfo.cfg']) == 0:
                # if minion location exists
                if subprocess.call(['ls', minion]) == 0:
                    # locations are valid

                    # is another user already on that page? If so, bounce this user
                    if subprocess.call(['ls', nanocas_location + 'analysis_busy']) == 0:
                        error.append({'message': 'This route is busy. Please try again!'})
                    else:

                        analysis_started_date = None
                        if subprocess.call(['ls', nanocas_location + 'analysis_started']) == 0:
                            with open(nanocas_location + 'analysis_started', 'r') as f:
                                analysis_started_date = f.readline()
                        else:
                            import datetime, time
                            d = datetime.datetime.utcnow()
                            for_js = int(time.mktime(d.timetuple())) * 1000
                            analysis_started_date = for_js
                            with open(nanocas_location + 'analysis_started', 'w') as f:
                                f.write(str(analysis_started_date))

                        subprocess.call(['touch', nanocas_location + 'analysis_busy'])
                        return render_template('analysis.html', app_loc=nanocas_location, minion_loc=minion,
                                               start_time=analysis_started_date)
                else:
                    error.append({'message': 'MinION location is not valid.'})
            else:
                error.append({'message': 'Alert configuration file is not found.'})
        else:
            error.append({'message': 'App location was not found'})
    return json.dumps(error)

@main.route('/validate_locations', methods=['POST', 'GET'])
def validate_locations():
    if (request.method == 'POST'):
        minION_location = request.form['minION']
        nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/') # Add to CONFIG

        minION_output_exists = os.path.exists(minION_location)
        app_output_exists = os.path.exists(nanocas_location) 

        logger.debug("minION_output = " + str(minION_output_exists))
        logger.debug("app_output_exists = " + str(app_output_exists))

        # create nanocas location if not excistant
        if not app_output_exists:
            os.mkdir(nanocas_location) 
            os.chmod(nanocas_location, mode=0o755)
            app_output_exists = True

        if (minION_output_exists and app_output_exists):
            return json.dumps({"code": 0, "message": "SUCCESS"})
        else:
            if not minION_output_exists:
                return json.dumps([{"code": 1, "message": f"Invalid minION location (err code {minION_output_exists})"}])
            elif not app_output_exists:
                return json.dumps([{"code": 1, "message": f"Invalid nanocas location (err code {app_output_exists})"}])
            else:
                return json.dumps([{"code": 1, "message": f"Unknown location error (minION_output_exists: {minION_output_exists}, nanocas_location: {app_output_exists}, query_output: {query_output})"}])
    else:
        return "N/A"

@main.route('/get_coverage', methods=['GET'])
def get_coverage():
    project_id = request.args.get('projectId')
    coverage_file = os.path.join(NANOCAS_DIR, project_id, 'coverage.csv')
    if not os.path.exists(coverage_file):
        return jsonify({'error': 'Coverage file not found'}), 404

    alert_cfg_file = os.path.join(NANOCAS_DIR, project_id, 'alertinfo.cfg')
    try:
        with open(alert_cfg_file, 'r') as f:
            alert_cfg = json.load(f)
        ref_to_name = {q['header']: q['name'] for q in alert_cfg['queries']}
    except Exception as e:
        logger.error(f"Error loading alert config: {e}")
        ref_to_name = {}

    try:
        with open(coverage_file, 'r') as f:
            lines = f.readlines()[1:]  # Skip header
        data = []
        for line in lines:
            timestamp, ref, avg_depth, breadth, read_count = line.strip().split(',')
            name = ref_to_name.get(ref, ref)  # Map reference to alert sequence name
            data.append({
                'timestamp': timestamp,
                'reference': name,
                'avg_depth': float(avg_depth),
                'breadth': float(breadth),
                'read_count': int(read_count)
            })
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error reading coverage file: {e}")
        return jsonify({'error': 'Error processing coverage data'}), 500

@main.route('/index_devices', methods=['GET'])
def index_devices():
    if (request.method == 'GET'):
        devices = []
        indexed_devices = LinuxNotification.index_devices()
        if len(indexed_devices) > 0:
            for device in indexed_devices:
                if device.state != "STATE_HARDWARE_REMOVED" \
                    or device.state != "STATE_HARDWARE_ERROR" \
                    or device.state != "STATE_SOFTWARE_ERROR":
                    devices.append(device.name)
                    LinuxNotification.send_notification(device.name, "Device discovered by nanocas", severity=1)
        
        return json.dumps(devices)
    
def validate_cache(cache_path=CACHE_PATH):
    if not os.path.isfile(cache_path):
        if not os.path.isdir(NANOCAS_DIR):
            os.mkdir(NANOCAS_DIR)
        open(CACHE_PATH, 'a').close()
        logger.warning(f"No cache found! Generated empty cache file...")
    pass