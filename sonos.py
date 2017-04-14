# High level library to deal with sonos
import soco
import soco.snapshot
from time import sleep

class SonosDeviceNotFoundError(Exception):
    def __init__(self):
        pass

class Sonos(object):

    def __init__(self):
        self.discover()
        if self.devices is None:
            print('Could not find any devices in startup')

    def discover(self):
        self.devices = soco.discover()

    def get_device_by_name(self, name):
        for dev in self.devices:
            if dev.player_name == name:
                return dev
        raise SonosDeviceNotFoundError()

    def get_current_transport_state(self, dev):
        info = dev.get_current_transport_info()
        print(info)
        return info['current_transport_state']

    def isStopped(self, dev):
        return self.get_current_transport_state(dev)  == 'STOPPED'

    def isPlaying(self, dev):
        return self.get_current_transport_state(dev) == 'PLAYING'

    def stop(self, dev):
        if self.isStopped(dev):
            return

        dev.stop()
        while not self.isStopped(dev):
            sleep(0.5)

    def play(self, dev, uri):
        # Synchronously play uri
        # 1. send play request
        # 2. ensure track starts playing
        # 3. ensure track is playing every second
        # 4. return once track is done
        self.stop(dev)
        assert self.isStopped(dev)

        enter = True
        while not self.isPlaying(dev):
            if enter:
                dev.play_uri(uri)
                enter = False
        assert self.isPlaying(dev)

        while self.isPlaying(dev):
            sleep(0.5)
