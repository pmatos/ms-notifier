import datetime
import time
from threading import Thread
from ivona_api import ivona_api
import boto3
import logging
import collections
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import http.client
import cgi
import urllib
import enum
import queue
import sonos # our high level sonos library

IVONA_ACCESS = 'GDNAJNH6ZRJLOPDJ7E2A'
IVONA_SECRET = 'M60QJ3zzo9goFZnVm5VZaNmjyOHlFcAJ8gPbiDMA'

AMAZON_ACCESS = 'AKIAJPYBNKJRPJ3SASEA'
AMAZON_SECRET = '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'

HOST_NAME = ''
PORT_NUMBER = 35353
FILE_PORT_NUMBER = 35354

MP3_URL = 'https://s3.eu-central-1.amazonaws.com/sounds.matos-sorge/bell.mp3'
HELLO_URI = 'x-sonos-spotify:spotify%3atrack%3a6HMvJcdw6qLsyV1b5x29sa?sid=9&flags=8224&sn=1'

# Global notification queue
q = queue.Queue()

class NotificationType(enum.Enum):
    STD_BELL = 0  # Standard bell notification

class Notification(object):
    def __init__(self, ntype):
        # Notification type is a value from NotificationType
        self.ntype = ntype

    def run(self):
        # Runs the action for the notification
        pass

class BellNotification(Notification):
    def __init__(self):
        super().__init__(NotificationType.STD_BELL)

    def run(self):
        s = Sonos() # Our sonos system

        # get state
        state = s.save_state()

        g = s.party_mode() # set system to party mode and return the group
        g.set_volume(40)   # set group volume
        g.play_uri('http://localhost:{}/ComputerMagic.mp3'.format(FILE_PORT_NUMBER))

        s.restore_state(state)

def save_system_state():
    """Saves system state into a Sonos State variable."""
    # Need to save:
    # * groups
    # * for each speaker:
    # ** volumes
    # ** if currently playing music, where is it playing?
    d = {}
    for spk in soco.discover():
        print('Saving state of {}'.format(spk.player_name))
        d[spk.player_name] = soco.snapshot.Snapshot(spk, snapshot_queue=True)
    return d

def restore_system_state(state):
    for spk, snapshot in state.items():
        print('Restoring {}'.format(spk.player_name))
        snapshot.restore()

def test():
    save_system_state()
    play_morningchime()
    restore_system_state()

def find_spk(name):
    """Returns the speaker with a given name or None."""
    speakers = soco.discover()
    for spk in speakers:
        if spk.player_name == name:
            return spk
    return None


def play_morningchime():
    """Plays morning chime to dining room speaker."""
    morningspk = find_spk('Dining Room')

    # Available on 05.08.2016
    #  fr-FR: Celine, Mathieu
    # pt-BR: Vitoria, Ricardo
    # sv-SE: Astrid
    # en-GB: Amy, Brian, Emma
    # cy-GB: Gwyneth, Geraint
    # en-AU: Nicole, Russell
    # da-DK: Naja, Mads
    # it-IT: Carla, Giorgio
    # es-US: Penelope, Miguel
    # pt-PT: Cristiano, Ines
    # de-DE: Marlene, Hans
    # nl-NL: Lotte, Ruben
    # en-IN: Raveena
    # en-GB-WLS: Gwyneth, Geraint
    # nb-NO: Liv
    # en-US: Salli, Joey, Chipmunk, Eric, Idra, Kimberly
    # is-IS: Dora, Karl
    # ro-RO: Carmen
    # fr-CA: Chantal
    # ru-RU: Maxim, Tatyana
    # tr-TR: Filiz
    # es-ES: Conchita, Enrique
    # pl-PL: Agnieszka, Jacek, Ewa, Jan, Ma
    ivona = ivona_api.IvonaAPI(IVONA_ACCESS,
                               IVONA_SECRET)
    voicedata = ivona.get_available_voices('en-GB')

    # Best british voices: Amy, Brian
    voices = []
    for vd in voicedata:
        voices.append(vd['Name'])
    morningspk.unjoin()
    assert(morningspk.is_coordinator)
    morningspk.clear_queue()
    voices = ['Markene']
    for voicename in voices:
        print('creating tts with {}'.format(voicename))
        with open('{}-morning.mp3'.format(voicename), 'wb') as f:
            ivona.text_to_speech('Good morning. My name is {} and it is {} in this beautiful country of sausage and beer! Look at that, it is {}, what a late riser you are. Chop, chop, time to school and work.'.format(voicename, datetime.datetime.today().strftime('%A, %B %d'), datetime.datetime.today().strftime('%H %M')),
                                 f, voice_name=voicename, language='en-GB')

        print('uploading to amazon')
        s3 = boto3.resource('s3', 'eu-central-1',
                            aws_access_key_id=AMAZON_ACCESS,
                            aws_secret_access_key=AMAZON_SECRET)
        k = s3.Object('sounds.matos-sorge', 'tmp/{}-morning.mp3'.format(voicename))
        k.put(Body=open('{}-morning.mp3'.format(voicename), 'rb'))
        k.Acl().put(ACL='public-read')

        morningspk.add_uri_to_queue('https://s3.eu-central-1.amazonaws.com/sounds.matos-sorge/tmp/{}-morning.mp3'.format(voicename))

    print('playing in speaker {}'.format(morningspk.player_name))
    morningspk.play_from_queue(0)


def play_child_call(name):
    callstr = '{} is calling you.'.format(name)
    filename = '{}-call.mp3'.format(name)

    ivona = ivona_api.IvonaAPI(IVONA_ACCESS, IVONA_SECRET)

    gym = find_spk('Gym')
    office = find_spk('Office')

    with open(filename, 'wb') as f:
        ivona.text_to_speech(callstr, f, voice_name='Amy', language='en-GB')

    s3 = boto3.resource('s3', 'eu-central-1',
                        aws_access_key_id=AMAZON_ACCESS,
                        aws_secret_access_key=AMAZON_SECRET)
    k = s3.Object('sounds.matos-sorge', filename)
    k.put(Body=open(filename, 'rb'))
    k.Acl().put(ACL='public-read')

    uri = 'https://s3.eu-central-1.amazonaws.com/sounds.matos-sorge/{}'\
          .format(filename)
    office.play_uri(uri)


def play_kimberly():
    play_child_call('Kimberly')


def play_linus():
    play_child_call('Linus')


def play_hello():
    """Plays the 'Hello, is it me you're looking for' by Lionel Ritchie
    from Spotify"""
    state = save_system_state()

    # unjoin so we can grab the office speaker
    office = find_spk('Office')
    if office is None:
        print("Can't find office")
        return

    # set volume
    office.unjoin()
    office.volume = 40
    office.play_uri(HELLO_URI, start=False)
    office.seek('00:00:42')
    office.play()
    time.sleep(9)
    office.stop()

    restore_system_state(state)

def decode_byte_dicts(data):
    if isinstance(data, bytes):
        return data.decode('utf-8')
    elif isinstance(data, collections.Mapping):
        return dict(map(decode_byte_dicts, data.items()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(decode_byte_dicts, data))
    else:
        return data


class MSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        ctype, pdict = cgi.parse_header(self.headers.get_content_type())
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif (ctype == 'application/x-www-form-urlencoded'
              or ctype == 'text/plain'):
            length = int(self.headers['Content-Length'])
            postvars = urllib.parse.parse_qs(self.rfile.read(length),
                                             keep_blank_values=1)
        else:
            postvars = {}

        vars = decode_byte_dicts(postvars)
        logging.info('request variables are {}'.format(vars))

        ntype = vars['type'][0]
        logging.info("received notification of type `{}'".format(ntype))

        if ntype == 'bell':
            notification = BellNotification()
            q.put(notification)
        elif ntype == 'kimcall':
            play_kimberly_call()
        elif ntype == 'linuscall':
            play_linus_call()
        elif ntype == 'morningchime':
            play_morningchime()

class FileHandler(BaseHTTPRequestHandler):
    def __init__(self):
        pass

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class NotificationWorker(Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        # Called when it's started by thread
        while True:
            logging.info("waiting notification")
            item = q.get() # blocking until there's an item
            logging.info("dequeued notification `{}'".format(item))
            item.run()     # run notification

def serve_files():
    logging.info("File Server Starts - {}:{}".format(HOST_NAME, FILE_PORT_NUMBER))
    filehttpd = ThreadingHTTPServer((HOST_NAME, FILE_PORT_NUMBER), FileHandler)
    filehttpd.serve_forever()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    logging.info('Starting Matos-Sorge notification daemon')

    # Start fike server in thread
    Thread(target=serve_files).start()

    logging.info("Notification Server Starts - {}:{}".format(HOST_NAME, PORT_NUMBER))
    httpd = ThreadingHTTPServer((HOST_NAME, PORT_NUMBER), MSHandler)

    logging.info("Creating new thread to deal with notifications")
    NotificationWorker().start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.warning('MS Notification got a keyboard interrupt, stopping')
        pass
    except:
        logging.warning('MS Notification got a interrupt, stopping')
    finally:
        httpd.server_close()
        logging.info("Notification server Stops - {}:{}".format(HOST_NAME, PORT_NUMBER))
    exit()
