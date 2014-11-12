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

running = True

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

class Wecker(object):
    
    def __init__(self, songs_path):
        self.songs_path = songs_path
        self.timers = []
        self.next_time = None
        self.songs = []
        self.curr_song_idx = 0
        
        self.is_stopped = True
        self.is_playing = False
        
    def update_next(self):
        self.next_time = min(self.timers)
        
    def play_current(self):
        music.load(self.songs[self.curr_song_idx])
        music.play()
        print('Playing: ', self.songs[self.curr_song_idx])
        
    def update_songs(self):
        self.songs = [ os.path.join(self.songs_path, f) for f in sorted(os.listdir(self.songs_path)) if f.endswith('.wav') or f.endswith('.mp3') or f.endswith('.ogg') ]
        
    def add_timer(self, time):
        self.timers.append(time)
        self.timers.sort()
        self.update_next()
        
    def delete_timer(self, time_idx):
        del self.timers[time_idx]
        self.update_next()
        
    def main_loop(self):
        print("Started wecker loop...")
        print('Songs to be played are:')
        for song in self.songs:
            print('  ', song)
            
        self.update_next()
        while running:
            #print(music.get_busy())
            #if not music.get_busy() and self.is_playing:
            for event in pygame.event.get():
                if event.type == SONG_END and self.is_playing:
                    print('Play next')
                    self.curr_song_idx = (self.curr_song_idx + 1) % len(self.songs)
                    self.play_current()
            
            if self.next_time <= datetime.now():
                print('Start beeping at ', datetime.now())
                self.timers.remove(self.next_time)
                self.update_next()
                self.is_playing = True
                self.is_stopped = False
                self.curr_song_idx = 0
                self.play_current()
                
            if not self.is_stopped and not self.is_playing:
                print('Music stopped')
                music.stop()
                self.is_stopped = True
            time.sleep(1)

class WeckerWebServer(SimpleHTTPRequestHandler):
    
    enc = "utf-8"
    wecker = None
    
    def do_GET(self):
        r = []
        self.build_head(r)
        request = parse.urlparse(self.path)
        path = request.path
        query = parse.parse_qs(request.query)
        #if path.startswith('/'):
        #    self.view_syllables(r, query)
        if 'stop' in query:
            print('Stopping the music')
            self.wecker.is_playing = False
        if 'delete_timer' in query:
            try:
                timer_i = int(query['delete_timer'][0])
                self.wecker.delete_timer(timer_i)
            except:
                pass
        if 'new_timer' in query:
            new_timer = datetime.strptime(query['new_timer'][0], TIME_FORMAT)
            self.wecker.add_timer(new_timer)
        
        self.build_body(r)
        self.view_overview(r, query)
        
        encoded = '\n'.join(r).encode(self.enc)
        self.send_headers(encoded)
        self.wfile.write(encoded)
        
    def view_overview(self, r, q):
        r.append('<h1>Overview</h1>')
        r.append('<h3>Songs:</h3>')
        r.append('<table>')
        for i, song in enumerate(self.wecker.songs):
            r.append('<tr><td>')
            if self.wecker.curr_song_idx == i and self.wecker.is_playing:
                r.append('->')
            r.append('</td><td>')
            r.append(song)
            r.append('</td></tr>')
        r.append('</table>')
        
        r.append('<h3>Timers:</h3>')
        r.append('<table>')
        for i, timer in enumerate(self.wecker.timers):
            r.append('<tr><td>')
            if self.wecker.next_time == timer:
                r.append('->')
            r.append('</td><td>')
            r.append('<a href="?delete_timer=%d">X</a>' % i)
            r.append('</td><td>')
            r.append(str(timer))
            r.append('</td></tr>')
        r.append('</table>')
        
        r.append('<form method="get" action="">')
        r.append('Add new timer: <input type="text" name="new_timer" value="%s"/>' % datetime.now().strftime(TIME_FORMAT))
        r.append('<input type="submit" value="Add"/>')
        r.append('</form>')
        
        r.append('<a href="?stop=1">Stop The Music!</a>')
        
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
    
    wecker = Wecker(r'../Music')
    wecker.update_songs()
    wecker.add_timer(datetime.now() + timedelta(seconds=5))
    wecker.add_timer(datetime.now() + timedelta(minutes=2))
    wecker.add_timer(datetime.now() + timedelta(hours=5))
    wecker_thread = threading.Thread(target=wecker.main_loop)
    WeckerWebServer.wecker = wecker
    
    port = 6666
    
    Handler = WeckerWebServer
    httpd = SocketServer.TCPServer(("", port), Handler)
    wecker_thread.start()
    time.sleep(0.01)
    print("Serve at port", port)
    try:
        httpd.serve_forever()
    except:
        running = False

if __name__ == '__main__':
    pass
