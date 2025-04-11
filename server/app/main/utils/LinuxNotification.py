
import subprocess
from dataclasses import dataclass
from minknow_api.manager import Manager
import logging

logger = logging.getLogger('nanocas')

@dataclass
class LinuxNotification():
    
    def index_devices(host="127.0.0.1", port=None):
        device_index = []
        try:
            manager = Manager(host=host, port=port)
            device_index = [position for position in manager.flow_cell_positions()]
        except:
            pass
        return device_index
        

    def get_device(device_name, host="127.0.0.1", port=None):
        for device in LinuxNotification.index_devices(host, port):
            if device.name == device_name:
                print(type(device))
                return device
        logger.error(f"Error: Could not find device {device_name}")
        return None

    def test_connection( device_name, msg="This is a linux test connection"):
        LinuxNotification.send_notification(msg)
        pass

    def send_notification(device_name, msg, severity=2):
        device = LinuxNotification.get_device(device_name)
        if device is None:
            logger.error(f"Cannot send notification: device {device_name} not found")
            return
        connection_address = device.connect()
        try:
            subprocess.Popen(['notify-send', msg])
        except:
            logger.error("Error: unable to send linux notification, are you running nanocas on linux?")
        connection_address.log.send_user_message(severity=severity, user_message=msg)
        logger.debug(connection_address.device.get_device_state())

