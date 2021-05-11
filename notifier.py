import sys
import time
import os
from subprocess import call

# path append for development only
import soco

import collections.abc
import http.server
import http.client
import cgi
import urllib
import socket
from mutagen.mp3 import MP3

from urllib.parse import quote
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread

HOST_NAME = ''
PORT_NUMBER = 35353

class LocalHttpServer(Thread):
    """A simple HTTP Server in its own thread"""

    def __init__(self, port):
        super().__init__()
        self.daemon = True

        # Find a free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        
        handler = SimpleHTTPRequestHandler
        self.httpd = TCPServer(("", port), handler)

    def run(self):
        """Start the server"""
        print("Start HTTP server")
        self.httpd.serve_forever()

    def stop(self):
        """Stop the server"""
        print("Stop HTTP server")
        self.httpd.socket.close()

def play_bell():
    """This function plays a bell in partymode but restore the
    state of the system afterwards."""

    # Find Dining Room player
    spk = soco.discovery.by_name("Dining Room")
    print('Found dining room speaker: {}'.format(spk))

    spk_in_group_p = sum(1 for _ in spk.group.members) > 1
    print(' * spk is in group: {}'.format(spk_in_group_p))
    
    groupuid = None
    if spk_in_group_p:
        groupuid = spk.group.uid
        print(' * spk group id: {}'.format(groupuid))
    mute_p = spk.mute
    print(' * spk muted: {}'.format(mute_p))
    
    volume = spk.volume
    print(' * spk volume: {}'.format(volume))

    if spk_in_group_p:
        spk.unjoin()
        print('sent unjoin request')
        still_in_group = True
        while still_in_group:
            print('waiting to unjoin')
            time.sleep(0.5)
            still_in_group = sum(1 for _ in spk.group.members) > 1
            
    # play
    # To play the local file, we start a new
    print('setting volume to 50 and playing bell')
    spk.mute = False
    spk.volume = 50
    play_uri(spk, 'assets/bell.mp3')

    # restore
    print('restoring volume to {}'.format(volume))
    spk.volume = volume
    print('restoring mute setting to {}'.format(mute_p))
    spk.mute = mute_p
    
    if spk_in_group_p:
        print('trying to find group to rejoin')
        grp = None
        for g in spk.all_groups:
            if g.uid == groupuid:
                print('found group with uid: {}'.format(g.uid))
                grp = g
        if grp:
            print('asking to rejoin group {} with coordinator'.format(grp, grp.coordinator))
            spk.join(grp.coordinator)

def detect_ip_address():
    """Return the local ip-address"""
    # Rather hackish way to get the local ip-address, recipy from
    # https://stackoverflow.com/a/166589
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address

def play_uri(spk, mp3):
    path = os.path.join(*[quote(part) for part in os.path.split(mp3)])
    netpath = "http://{}:{}/{}".format(detect_ip_address(), port, path)
    number_in_queue = spk.add_uri_to_queue(netpath)
    spk.play_from_queue(number_in_queue - 1)

    audio = MP3(mp3)
    mp3_length = int(audio.info.length)
    time.sleep(mp3_length)
    
    spk.stop()
    spk.remove_from_queue(number_in_queue - 1)
    
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
        elif vars['type'] == ['coffeemachine']:
            if vars['value'] == ['on']:
                coffeemachine_on()
            elif vars['value'] == ['off']:
                coffeemachine_off()

if __name__ == '__main__':
    # Start server to locally serve files
    local_file_server = LocalHttpServer()
    local_file_server.start()

    # Start server to listen to loxone requests
    server_class = http.server.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MSHandler)
    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    # Stop loxone server
    httpd.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER))

    # Stop local files server
    local_file_server.stop()
