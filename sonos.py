# High level library to deal with sonos
import soco
import soco.snapshot
from time import sleep

class SonosDeviceNotFoundError(Exception):
    def __init__(self):
        pass

class Sonos(object):

    def __init__(self):
        self.devices = self.discover()
        if self.devices is None:
            print('Could not find any devices in startup')

    def discover(self):
        self.devices = soco.discover()

    def get_device_by_name(self, name):
        for dev in self.devices:
            if dev.player_name == name:
                return dev
        raise SonosDeviceNotFoundError()

    def isStopped(self, dev):
        return dev.get_current_transport_info()['current_transport_state'] == 'STOPPED'

    def stop(self, dev):
        if self.isStopped(dev):
            return

        dev.stop()
        while dev.get_current_transport_info()['current_transport_state'] != 'STOPPED':
            sleep(0.1)

    def play(self, dev, uri):
        # Synchronously play uri
        # 1. send play request
        # 2. ensure track starts playing
        # 3. ensure track is playing every second
        # 4. return once track is done
        self.stop(dev)
        dev.play_uri(uri)
        while dev.get_current_transport_info()['current_transport_state'] == 'PLAYING':
            sleep(0.1)
