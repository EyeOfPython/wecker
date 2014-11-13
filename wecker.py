'''
Created on 12.11.2014

@author: Tobias Ruck
'''
from __future__ import print_function

from SimpleHTTPServer import SimpleHTTPRequestHandler
import urlparse as parse

from datetime import datetime, timedelta, date
import os, time

import threading

from icalendar import Calendar
from dateutil.tz import tzlocal
from urllib2 import urlopen

from pprint import pprint
    
import pygame
pygame.init()
pygame.mixer.init()
music = pygame.mixer.music

SONG_END = pygame.USEREVENT + 1
music.set_endevent(SONG_END)

running = True

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
CALENDER_UPDATE_INTERVAL = timedelta(hours=3)

class Wecker(object):
    
    def __init__(self, songs_path):
        self.songs_path = songs_path
        self.timers = []
        self.next_time = None
        self.songs = []
        self.curr_song_idx = 0
        
        self.last_calender_update = datetime.now()
        self.calendar_urls = []
        self.calendar_timers = []
        self.blocked_calendar_timers = set()
        
        self.is_stopped = True
        self.is_playing = False
        
    def update_next(self):
        self.next_time = min(self.timers + [ ct['time'] for ct in self.calendar_timers if ct['uid'] not in self.blocked_calendar_timers ])
        
        now = datetime.now().replace(tzinfo=tzlocal())
        blocked_and_passed = [ ct for ct in self.calendar_timers 
                                    if ct['uid'] in self.blocked_calendar_timers 
                                       and ct['time'] < now ]
        for b in blocked_and_passed:
            self.calendar_timers.remove(b)
            self.blocked_calendar_timers.discard(b['uid'])
        
    def update_songs(self):
        self.songs = [ os.path.join(self.songs_path, f) for f in sorted(os.listdir(self.songs_path)) if f.endswith('.wav') or f.endswith('.mp3') or f.endswith('.ogg') ]
        
    def update_calendars(self):
        self.calendar_timers = []
        now = datetime.now().replace(tzinfo=tzlocal())
        today = datetime(*date.today().timetuple()[:3]).replace(tzinfo=tzlocal())
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=5)
        week = {} # earliest time to wake up
        for url in self.calendar_urls:
            calender_src = urlopen(url).read().decode('utf-8')
            calendar = Calendar.from_ical(calender_src)
            
            for item in calendar.subcomponents:
                if item.name == 'VEVENT':
                    dstart = item['DTSTART'].dt
                    if start_of_week <= dstart <= end_of_week and dstart > now:
                        if dstart.date() not in week or dstart < week[dstart.date()]['DTSTART'].dt:
                            week[dstart.date()] = item
                            
        self.calendar_timers = [ { 'title': unicode(item['SUMMARY']), 'time': item['DTSTART'].dt, 'uid': hash(str(item['UID'])) } 
                                 for item in week.values() ]
        pprint(self.calendar_timers)
        
    def play_current(self):
        music.load(self.songs[self.curr_song_idx])
        music.play()
        print('Playing: ', self.songs[self.curr_song_idx])
        
    def add_timer(self, time):
        time = time.replace(tzinfo=tzlocal())
        self.timers.append(time)
        self.timers.sort()
        self.update_next()
        
    def delete_timer(self, time_idx):
        del self.timers[time_idx]
        self.update_next()
        
    def add_calendar(self, url):
        self.calendar_urls.append(url)
        
    def remove_calendar(self, url):
        self.calendar_urls.remove(url)
        
    def deffered_calendar_update(self):
        print('Calender update at', datetime.now())
        def _update():
            self.update_calendars()
            self.update_next()
        threading.Thread(target=_update).start()
        
    def toggle_block_calendar_timer(self, uid):
        self.blocked_calendar_timers ^= set( [uid] )
        self.update_next()
        
    def block_calendar_timer(self, uid):
        self.blocked_calendar_timers.add(uid)
        self.update_next()
        
    def unblock_calendar_timer(self, uid):
        self.blocked_calendar_timers.remove(uid)
        self.update_next()
        
    def main_loop(self):
        print("Started wecker loop")
        print('Songs to be played are:')
        for song in self.songs:
            print('  ', song)
            
        self.update_next()
        while running:
            for event in pygame.event.get():
                if event.type == SONG_END and self.is_playing:
                    print('Play next')
                    self.curr_song_idx = (self.curr_song_idx + 1) % len(self.songs)
                    self.play_current()
            
            if self.next_time <= datetime.now().replace(tzinfo=tzlocal()):
                print('Start beeping at ', datetime.now(), 'for', self.next_time)
                if self.next_time in self.timers:
                    self.timers.remove(self.next_time)
                for c in self.calendar_timers:
                    if c['time'] == self.next_time:
                        self.calendar_timers.remove(c)
                        self.blocked_calendar_timers.discard(c['uid'])
                        break
                self.update_next()
                self.is_playing = True
                self.is_stopped = False
                self.curr_song_idx = 0
                self.play_current()
                
            if self.last_calender_update + CALENDER_UPDATE_INTERVAL <= datetime.now():
                print('3 hour calender update at', datetime.now())
                self.last_calender_update = datetime.now()
                self.deffered_calendar_update()
                
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
        
        if 'block_ctimer' in query:
            try:
                block_id = int(query['block_ctimer'][0])
            except:
                pass
            self.wecker.toggle_block_calendar_timer(block_id)
        
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
        
        r.append('<h3>User Timers:</h3>')
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
        
        r.append('<h3>Calendar Timers:</h3>')
        r.append('<table>')
        for ct in self.wecker.calendar_timers:
            r.append('<tr><td>')
            if self.wecker.next_time == ct['time']:
                r.append('->')
            r.append('</td><td>')
            r.append('<a href="?block_ctimer=%d">%s</a>' % (ct['uid'], 'UNBLOCK' if ct['uid'] in self.wecker.blocked_calendar_timers else 'block' ))
            r.append('</td><td>')
            r.append(ct['title'])
            r.append('</td><td>')
            r.append(str(ct['time']))
            r.append('</td></tr>')
        r.append('</table>')
        
        r.append('<p>Next calender update: %s</p>' % (self.wecker.last_calender_update + CALENDER_UPDATE_INTERVAL))
        
        r.append('<form method="get" action="">')
        r.append('Add new user timer: <input type="text" name="new_timer" value="%s"/>' % datetime.now().strftime(TIME_FORMAT))
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
    
    wecker = Wecker(r'../Music')
    wecker.add_calendar("https://www.martingansler.de/dhbw/cal/dhbw.php")
    print('Initialize calendar')
    wecker.update_calendars()
    
    wecker.update_songs()
    wecker.add_timer(datetime(2020,1,1))
    wecker_thread = threading.Thread(target=wecker.main_loop)
    WeckerWebServer.wecker = wecker
    
    port = 16666
    
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
