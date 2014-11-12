'''
Created on 12.11.2014

@author: Tobias Ruck
'''
from __future__ import print_function

from SimpleHTTPServer import SimpleHTTPRequestHandler
import urlparse as parse

from datetime import datetime, timedelta
import os, time

import pygame
pygame.init()
pygame.mixer.init()
music = pygame.mixer.music

SONG_END = pygame.USEREVENT + 1
music.set_endevent(SONG_END)

class Wecker(object):
    
    def __init__(self, songs_path):
        self.songs_path = songs_path
        self.times = []
        self.next_time = None
        self.songs = []
        self.curr_song_idx = 0
        
        self.is_stopped = True
        self.is_playing = False
        
    def update_next(self):
        self.next_time = min(self.times)
        
    def play_current(self):
        music.load(self.songs[self.curr_song_idx])
        music.play()
        print('Playing: ', self.songs[self.curr_song_idx])
        
    def update_songs(self):
        self.songs = [ os.path.join(self.songs_path, f) for f in sorted(os.listdir(self.songs_path)) if f.endswith('.wav') or f.endswith('.mp3') or f.endswith('.ogg') ]
        
    def main_loop(self):
        print("Started wecker loop...")
        print('Songs to be played are:')
        for song in self.songs:
            print('  ', song)
            
        self.update_next()
        while True:
            #print(music.get_busy())
            #if not music.get_busy() and self.is_playing:
            for event in pygame.event.get():
                if event.type == SONG_END and self.is_playing:
                    print('Play next')
                    self.curr_song_idx = (self.curr_song_idx + 1) % len(self.songs)
                    self.play_current()
            
            if self.next_time <= datetime.now():
                print('Start beeping at ', datetime.now())
                self.times.remove(self.next_time)
                self.update_next()
                self.is_playing = True
                self.is_stopped = False
                self.curr_song_idx = 0
                self.play_current()
                
            if not self.is_stopped and not self.is_playing:
                print('Music stopped')
                music.stop()
            time.sleep(1)

class WeckerWebServer(SimpleHTTPRequestHandler):
    
    enc = "utf-8"
    
    def do_GET(self):
        r = []
        self.build_head(r)
        request = parse.urlparse(self.path)
        path = request.path
        query = parse.parse_qs(request.query)
        #if path.startswith('/'):
        #    self.view_syllables(r, query)
        
        self.build_body(r)
        
        encoded = '\n'.join(r).encode(self.enc)
        self.send_headers(encoded)
        self.wfile.write(encoded)
        
    def view_overview(self, r, q):
        r.append('<h1>Overview</h1>')
        
    def build_head(self, r):
        title = 'Overview' 
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % self.enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n')
        
    def build_body(self, r):
        r.append('\n</body>\n</html>\n')
        
    def send_headers(self, text):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=%s" % self.enc)
        self.send_header("Content-Length", str(len(text)))
        self.end_headers()

if __name__ == '__main__':
    import SocketServer
    import threading
    
    wecker = Wecker(r'L:\Users\Tobias Ruck\Music\test')
    wecker.update_songs()
    wecker.times.append(datetime.now() + timedelta(seconds=5))
    wecker.times.append(datetime.now() + timedelta(hours=5))
    wecker_thread = threading.Thread(target=wecker.main_loop)
    port = 6666
    
    Handler = WeckerWebServer
    httpd = SocketServer.TCPServer(("", port), Handler)
    wecker_thread.start()
    time.sleep(0.01)
    print("Serve at port", port)
    httpd.serve_forever()

if __name__ == '__main__':
    pass