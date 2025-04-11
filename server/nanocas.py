# FILE: ./nanocas.py
# The main entry point in the application

import logging
import sys
from app import create_app, socketio

# Configure the 'nanocas' logger
logger = logging.getLogger('nanocas')
if not logger.handlers:  # Prevent duplicate handlers
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

# Remove the old logging setup
# import logging.config
# from os import path
# logging.config.fileConfig("./server/logging.ini")
# log = logging.getLogger('nanocas')

app = create_app(debug=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5007)