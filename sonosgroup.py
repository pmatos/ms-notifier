class SonosGroup(object):

    def __init__(self, master, slaves):
        self.master = master
        self.slaves = slaves

    def get_master(self):
        return self.master

    def is_master(self, dev):
        return dev == self.get_master()

    def is_slave(self, dev):
        return dev in self.slaves

    # TODO implement __eq__, __ne__ and __hash__
