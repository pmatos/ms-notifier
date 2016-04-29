import sys
import time

# path append for development only
sys.path.append('/home/pmatos/Projects/SoCo')
import soco

import collections
import http.server
import http.client
import cgi
import urllib

HOST_NAME = ''
PORT_NUMBER = 35353

MP3_URL = 'https://s3.eu-central-1.amazonaws.com/sounds.matos-sorge/bell.mp3'


def save_system_state():
    return None


def restore_system_state(state):
    return


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
        elif ctype == 'application/x-www-form-urlencoded':
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
