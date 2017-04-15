# High level library to deal with sonos
import soco
import soco.snapshot
from sonosdevice import SonosDevice
from time import sleep

class SonosDeviceNotFoundError(Exception):
    def __init__(self):
        pass

class Sonos(object):

    def __init__(self):
        self.discover()
        if not self.devices:
            print('Could not find any devices in startup')

    def discover(self):
        devs = soco.discover()
        self.devices = []
        for d in devs:
            self.devices.append(SonosDevice(d))

    def get_device_by_name(self, name):
        for dev in self.devices:
            if dev.get_name() == name:
                return dev
        raise SonosDeviceNotFoundError()

    def get_groups(self):
        return None
