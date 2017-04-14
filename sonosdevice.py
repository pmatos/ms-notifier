class SonosDevice(object):
    def __init__(self, dev):
        self.dev = dev

    def get_name(self):
        return self.dev.player_name

    def get_current_transport_state(self):
        info = self.dev.get_current_transport_info()
        return info['current_transport_state']

    def isStopped(self):
        return self.get_current_transport_state() == 'STOPPED'

    def isPlaying(self):
        return self.get_current_transport_state() == 'PLAYING'

    def isTransitioning(self):
        return self.get_current_transport_state() == 'TRANSITIONING'

    def isPaused(self):
        return self.get_current_transport_state() == 'PLAYBACK_PAUSED'

    def stop(self):
        if self.isStopped():
            return

        self.dev.stop()
        while not self.isStopped():
            sleep(0.5)

    def play(self, uri):
        # Synchronously play uri
        # 1. send play request
        # 2. ensure track starts playing
        # 3. ensure track is playing every second
        # 4. return once track is done
        self.stop()
        assert self.isStopped()

        enter = True
        while not self.isPlaying():
            if enter:
                self.dev.play_uri(uri)
                enter = False
        assert self.isPlaying()

        while self.isPlaying():
            sleep(0.5)
