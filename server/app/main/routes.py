import ast
import json
import logging
import os
import gzip
import tempfile
import uuid
import subprocess
import glob
import pysam

from flask import session, render_template, request, abort, jsonify
from . import main
from .utils import LinuxNotification

logger = logging.getLogger('nanocas')

NANOCAS_DIR = os.path.join(os.path.expanduser('~'), '.nanocas')
CACHE_PATH = os.path.join(os.path.expanduser('~'), '.nanocas/.cache')

@main.route('/version', methods=['GET'])
def version():
    return json.dumps({"version": "v0.0.2", "name": "nanocas PoC"})

@main.route('/check_database_status', methods=['GET'])
def check_database_status():
    project_id = request.args.get('projectId')
    if not project_id:
        return jsonify({'error': 'projectId is required'}), 400
    nanocas_path = os.path.join(NANOCAS_DIR, project_id)
    mmi_files = glob.glob(os.path.join(nanocas_path, 'database', '*.mmi'))
    is_ready = len(mmi_files) > 0
    return jsonify({'is_ready': is_ready})

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
    uid_dir = os.path.join(os.path.expanduser('~'), '.nanocas/' + uid)
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
            return json.dumps({'status': 404, 'message': "Couldn't find the analysis data with UID: " + str(uid)})
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

        nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/')
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
                if minion is not None and subprocess.call(['ls', minion]) == 0:
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
        nanocas_location = os.path.join(os.path.expanduser('~'), '.nanocas/')

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
            timestamp, ref, depth, breadth, read_count = line.strip().split(',')
            name = ref_to_name.get(ref, ref)  # Map reference to alert sequence name
            data.append({
                'timestamp': timestamp,
                'reference': name,
                'depth': float(depth),
                'breadth': float(breadth),
                'read_count': int(read_count)
            })
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error reading coverage file: {e}")
        return jsonify({'error': 'Error processing coverage data'}), 500

@main.route('/index_devices', methods=['GET'])
def index_devices():
    if request.method == 'GET':
        devices = []
        indexed_devices = LinuxNotification.index_devices()
        if indexed_devices:
            for device in indexed_devices:
                if device.state not in ["STATE_HARDWARE_REMOVED", "STATE_HARDWARE_ERROR", "STATE_SOFTWARE_ERROR"]:
                    devices.append(device.name)
                    LinuxNotification.send_notification(device.name, "Device discovered by nanocas", severity=1)
        # Always return a valid JSON response
        return json.dumps(devices)
    # Explicitly return an empty list if not GET (should not happen)
    return json.dumps([])

@main.route('/upload_fasta', methods=['POST'])
def upload_fasta():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    temp_dir = tempfile.mkdtemp(dir=NANOCAS_DIR)
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)
    logger.debug(f"Uploaded FASTA file to {file_path}")
    return jsonify({'file_path': file_path})

@main.route('/upload_gff', methods=['POST'])
def upload_gff():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    temp_dir = tempfile.mkdtemp(dir=NANOCAS_DIR)
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)
    logger.debug(f"Uploaded GFF file to {file_path}")
    return jsonify({'file_path': file_path})

@main.route('/parse_fasta_headers', methods=['POST'])
def parse_fasta_headers():
    data = request.json
    file_path = data.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Invalid file path'}), 400
    headers = []
    try:
        if file_path.endswith('.gz'):
            with gzip.open(file_path, 'rt') as f:
                for line in f:
                    if line.startswith('>'):
                        headers.append(line[1:].strip())
        else:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('>'):
                        headers.append(line[1:].strip())
        logger.debug(f"Parsed {len(headers)} headers from {file_path}")
        return jsonify(headers)
    except Exception as e:
        logger.error(f"Error parsing FASTA headers: {e}")
        return jsonify({'error': str(e)}), 500

def parse_gff(gff_path, sequence_id):
    regions = []
    try:
        with open(gff_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    fields = line.strip().split('\t')
                    if len(fields) >= 5 and fields[0] == sequence_id:
                        start = int(fields[3])
                        end = int(fields[4])
                        attributes = fields[8] if len(fields) > 8 else ""
                        region_id = None
                        for attr in attributes.split(';'):
                            if attr.startswith('ID='):
                                region_id = attr[3:]
                                break
                        regions.append({'start': start, 'end': end, 'id': region_id})
    except Exception as e:
        logger.error(f"Error parsing GFF file {gff_path}: {e}")
    return regions

@main.route('/get_alignments', methods=['GET'])
def get_alignments():
    project_id = request.args.get('projectId')
    reference = request.args.get('reference')
    if not project_id or not reference:
        return jsonify({'error': 'projectId and reference are required'}), 400
    nanocas_path = os.path.join(NANOCAS_DIR, project_id)
    stable_bam = os.path.join(nanocas_path, 'merged_stable.bam') 
    stable_bam_index = stable_bam + '.bai'
    if not os.path.exists(stable_bam):
        return jsonify({'error': 'Stable BAM file not found'}), 404
    try:

        if not os.path.exists(stable_bam_index):
            return jsonify({'error': 'BAM index file not found'}), 404

        bam = pysam.AlignmentFile(stable_bam, "rb")
        if reference not in bam.references:
            return jsonify({'error': 'Reference not found in BAM file'}), 404
        ref_length = bam.lengths[bam.references.index(reference)]
        alignments = []
        for alignment in bam.fetch(reference):
            if not alignment.is_unmapped:
                start = alignment.reference_start
                end = alignment.reference_end
                strand = '-' if alignment.is_reverse else '+'
                alignments.append({'start': start, 'end': end, 'strand': strand})

        # Load and parse GFF file if present
        alert_cfg_file = os.path.join(nanocas_path, 'alertinfo.cfg')
        regions = []
        with open(alert_cfg_file, 'r') as f:
            alert_cfg = json.load(f)
            gff_file = alert_cfg.get('gff_file')
            if gff_file and os.path.exists(gff_file):
                regions = parse_gff(gff_file, reference)
                for region in regions:
                    count = sum(1 for aln in alignments if aln['start'] < region['end'] and aln['end'] > region['start'])
                    region['read_count'] = count

        bam.close()
        return jsonify({'ref_length': ref_length, 'alignments': alignments, 'regions': regions})
    except Exception as e:
        logger.error(f"Error getting alignments: {e}")
        print(e)
        return jsonify({'error': 'Error processing BAM file'}), 500

def validate_cache(cache_path=CACHE_PATH):
    if not os.path.isfile(cache_path):
        if not os.path.isdir(NANOCAS_DIR):
            os.mkdir(NANOCAS_DIR)
        open(CACHE_PATH, 'a').close()
        logger.warning(f"No cache found! Generated empty cache file...")
    pass