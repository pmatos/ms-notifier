# High level library to deal with sonos
from time import sleep
from typing import Set, Any
import soco
import soco.snapshot


class SonosDeviceNotFoundError(Exception):
    def __init__(self):
        pass

class SonosDeviceNotCoordinatorError(Exception):
    def __init__(self):
        pass

class SonosDevice(object):
    def __init__(self, dev):
        self.dev = dev

    def __hash__(self) -> int:
        return hash(self.get_uid())

    def __repr__(self) -> str:
        return "SonosDevice({})".format(self.get_name())

    def __eq__(self, other: Any) -> bool:
        return other.get_uid() == self.dev.uid

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def _get_raw(self) -> soco.SoCo:
        return self.dev

    def get_uid(self) -> str:
        return self.dev.uid

    def get_name(self) -> str:
        return self.dev.player_name

    def get_current_transport_state(self):
        info = self.dev.get_current_transport_info()
        return info['current_transport_state']

    def get_group(self) -> 'SonosGroup':
        return SonosGroup(self.dev.group)

    def is_stopped(self) -> bool:
        return self.get_current_transport_state() == 'STOPPED'

    def is_playing(self) -> bool:
        return self.get_current_transport_state() == 'PLAYING'

    def is_transitioning(self):
        return self.get_current_transport_state() == 'TRANSITIONING'

    def is_paused(self):
        return self.get_current_transport_state() == 'PLAYBACK_PAUSED'

    def is_coordinator(self) -> bool:
        return self == self.get_group().get_coordinator()

    def join(self, coordinator: 'SonosDevice') -> None:
        """Join current device in a group with master, and make master the coordinator."""
        if not coordinator.is_coordinator():
            raise SonosDeviceNotCoordinatorError()
        self.dev.join(coordinator._get_raw())

    def stop(self) -> None:
        if self.isStopped():
            return

        self.dev.stop()
        while not self.isStopped():
            sleep(0.5)

    def play(self, uri: str) -> None:
        # Synchronously play uri
        # 1. send play request
        # 2. ensure track starts playing
        # 3. ensure track is playing every second
        # 4. return once track is done
        self.stop()
        assert self.is_stopped()

        enter = True
        while not self.is_playing():
            if enter:
                self.dev.play_uri(uri)
                enter = False
        assert self.is_playing()

        while self.is_playing():
            sleep(0.5)

    def mute(self) -> None:
        self.dev.mute = True

    def unmute(self) -> None:
        self.dev.mute = False

    def is_mute(self) -> bool:
        return self.dev.mute


class SonosGroup(object):

    def __init__(self, group: soco.groups.ZoneGroup):
        self.raw_group = group
        self.coordinator = SonosDevice(group.coordinator)
        self.members = set(map(SonosDevice, group.members))

    def __hash__(self) -> int:
        return hash(self.raw_group.uid)

    def __repr__(self) -> str:
        repr_str = 'SonosGroup({}, {})'
        return repr_str.format(repr(self.coordinator),
                               ', '.join(map(repr, self.members)))

    def __eq__(self, other):
        return self.coordinator == other.get_coordinator() and \
            self.members == other.get_members()

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_coordinator(self) -> SonosDevice:
        return self.coordinator

    def get_members(self) -> Set[SonosDevice]:
        return self.members

    def is_alone(self) -> bool:
        return len(self.members) == 1

    def reinstate(self) -> None:
        # if group is still the same do nothing
        if self.coordinator.get_group() == self:
            return

        # setup groups once again
        for spk in self.members:
            if not spk == self.coordinator:
                spk.unjoin()
                spk.join(self.coordinator)


class SonosState(object):
    """Represents a state of the sonos system at the point of creation."""

    def __init__(self, system):
        # Grab groups


        # Grab mute information
        pass

class Sonos(object):

    def __init__(self):
        self.discover()
        if not self.devices:
            print('Could not find any devices in startup')

    def __repr__(self) -> str:
        repr_str = 'Sonos({})'
        return repr_str.format(','.join(map(repr, self.devices)))

    def discover(self) -> None:
        self.devices = set(map(lambda d: SonosDevice(d), soco.discover()))

    def get_devices(self) -> Set[SonosDevice]:
        return self.devices

    def get_device_by_name(self, name: str) -> SonosDevice:
        for dev in self.devices:
            if dev.get_name() == name:
                return dev
        raise SonosDeviceNotFoundError()

    def get_groups(self) -> Set[SonosGroup]:
        if not self.devices:
            return None

        anydev = next(iter(self.devices))
        return set(map(SonosGroup, anydev._get_raw().all_groups))
