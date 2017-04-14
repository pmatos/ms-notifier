import sys
import datetime
import time

# path append for development only
# sys.path.append('/home/pmatos/Projects/SoCo')
import soco
import soco.snapshot
from ivona_api import ivona_api
import boto3

import collections
import http.server
import http.client
import cgi
import urllib

IVONA_ACCESS='GDNAJNH6ZRJLOPDJ7E2A'
IVONA_SECRET='M60QJ3zzo9goFZnVm5VZaNmjyOHlFcAJ8gPbiDMA'

AMAZON_ACCESS='AKIAJPYBNKJRPJ3SASEA'
AMAZON_SECRET='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'

HOST_NAME = ''
PORT_NUMBER = 35353

MP3_URL = 'https://s3.eu-central-1.amazonaws.com/sounds.matos-sorge/bell.mp3'
HELLO_URI = 'x-sonos-spotify:spotify%3atrack%3a6HMvJcdw6qLsyV1b5x29sa?sid=9&flags=8224&sn=1'

def save_system_state():
    """Saves system state into a Sonos State variable."""
    # Need to save:
    # * groups
    # * for each speaker:
    # ** volumes
    # ** if currently playing music, where is it playing?
    return None


def restore_system_state(state):
    return


def find_spk(name):
    """Returns the speaker with a given name or None."""
    speakers = soco.discover()
    for spk in speakers:
        if spk.player_name == name:
            return spk
    return None


def play_morningchime():
    """Plays morning chime to dining room speaker."""
    morningspk = find_spk('Office')

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
    voices = []
    for vd in voicedata:
        voices.append(vd['Name'])
    morningspk.unjoin()
    assert(morningspk.is_coordinator)
    morningspk.clear_queue()
    for voicename in voices:
        print('creating tts with {}'.format(voicename))
        with open('{}-morning.mp3'.format(voicename), 'wb') as f:
            ivona.text_to_speech('Good morning. My name is {} and I am here to bring you good news. What a beautiful day it is. Rise and shine!'.format(voicename), f)

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


def play_bell():
    """This function plays a bell in partymode but restore the
    state of the system afterwards."""

    speakers = soco.discover()

    if speakers is None:
        print("Can't find speakers")
        exit()

    state = save_system_state()

    # unjoin so we can go to party mode
    for spk in speakers:
        spk.unjoin()

    # select one for master, doesn't matter which
    master = speakers.pop()
    master.partymode()

    # set volume
    master.volume = 40
    for spk in speakers:
        spk.volume = 40
    master.play_uri(MP3_URL)

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


class MSHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        print('headers are {}'.format(self.headers))
        ctype, pdict = cgi.parse_header(self.headers.get_content_type())
        print('ctype is {}'.format(ctype))
        print('params are {}'.format(pdict))
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif (ctype == 'application/x-www-form-urlencoded'
              or ctype == 'text/plain'):
            length = int(self.headers['Content-Length'])
            print('content length is {}'.format(length))
            postvars = urllib.parse.parse_qs(self.rfile.read(length),
                                             keep_blank_values=1)
        else:
            postvars = {}

        vars = decode_byte_dicts(postvars)
        print('vars are {}'.format(vars))
        if vars['type'] == ['bell']:
            play_bell()
        elif vars['type'] == ['kimcall']:
            play_kimberly_call()
        elif vars['type'] == ['linuscall']:
            play_linus_call()
        elif vars['type'] == ['morningchime']:
            play_morningchime()

if __name__ == '__main__':
    server_class = http.server.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MSHandler)
    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER))
