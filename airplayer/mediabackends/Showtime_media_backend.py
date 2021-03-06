import urllib2
import urllib
import time
import thread
import tempfile
import shutil
import os

import utils
import Image
from PIL.ExifTags import TAGS

from base_media_backend import BaseMediaBackend

class ShowtimeMediaBackend(BaseMediaBackend):
    """
    The Showtime backend is a backend for HTS Showtime, available here: https://github.com/andoma/showtime
    In addition to the standard dependencies, this backend uses Python Image Library. The dependency has been added to requirements.txt 
    """
    
    def __init__(self, host, port, username=None, password=None):
        super(ShowtimeMediaBackend, self).__init__(host, port, username, password)
        
        self._last_wakeup = None
        self._TMP_DIR = tempfile.mkdtemp()
        
        """
        Make sure the folder is world readable
        """
        os.chmod(self._TMP_DIR, 0755)
        
        self.log.debug('TEMP DIR: %s', self._TMP_DIR)
    
    def _http_api_request(self, command, parameters=None):
        """
        Perform a request to the Showtime http api.
        @return raw request result or None in case of error
        """
        
        self._wake_screen()        

        command = urllib.quote(command)

        url = 'http://%s/showtime/%s' % (self.host_string(), command)

        if parameters:
            url = url + "?" + urllib.urlencode(parameters)        

        self.log.debug("_http_api_request url %s", url)

        req = urllib2.Request(url)
        return self._http_request(req)
        
    def _send_notification(self, message):
        """
        Sends a notification to Showtime, this is displayed to the user as a popup.
        """
        self._http_api_request('notifyuser', {'msg': message})
        
    def _set_start_position(self, position_percentage):
        for i in range(3):
            response, error = self.set_player_position_percentage(position_percentage)
            if error:
                self.log.debug('Setting start position failed: %s', error)
                time.sleep(1)
                continue

            self.log.debug('Setting start position succeeded')    
            return

        self.log.warning('Failed to set start position')
        
    def _wake_screen(self):
        now = time.time()
        
        if not self._last_wakeup or now - self._last_wakeup > 60:
            self._last_wakeup = now
            
            self.log.debug('Sending wake event')
            self._http_api_request('input/action/DisableScreenSaver')
        
    def cleanup(self):
        shutil.rmtree(self._TMP_DIR)                          
        
    def stop_playing(self):
        """
        Stop playing media.
        """
        self._http_api_request('input/action/Stop')
        
    def show_picture(self, data):
        """
        Show a picture.
        @param data raw picture data.
        """

        utils.clear_folder(self._TMP_DIR)
        filename = 'picture%d.jpg' % int(time.time())
        path = os.path.join(self._TMP_DIR, filename)
        
        f = open(path, 'wb')
        f.write(data)
        f.close()

        img = Image.open(path)
        """
        The image is loaded and saved because Showtimes image viewer can't handle many of the image that come straight from an iPhone.
        Since PIL does not retain the Exif data, we must rotate the image if needed instead.
        """
        exif = img._getexif()
        if exif != None:
            for tag, value in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == 'Orientation':
                    if value == 3: img = img.rotate(180)
                    if value == 6: img = img.rotate(270)
                    if value == 8: img = img.rotate(90)
                    break
                
        img.save(path);

        path = "file://" + path

        self.log.debug("filename %s", path);
        self.open_url(path)
        
    def open_url(self, url):
        """
        Open file at the given location.
        Does not work very well with showtime at the moment.
        """
        self._http_api_request('open', {'url': url})
 
    def play_movie(self, url):
        """
        Play a movie from the given location.
        """
        self.open_url(url)

    def notify_started(self):
        """
        Notify the user that Airplayer has started.
        """
        self._send_notification('Airplayer started')
        
    def is_playing(self):
        response = self.get_player_state()
        
        if not response:
            return False
            
        return (response == 'play')
    
    def get_player_state(self):
        """
        Return the current state for the given player. 
        @param player a valid player (e.g. videoplayer, audioplayer etc)
        """
        response = self._http_api_request('prop/global/media/current/playstatus')

        return response;
        
    def _pause(self):
        """
        Pause media playback.
        """
        self._http_api_request('input/action/Pause')       
        
    def pause(self):
        self._pause()
    
    def _play(self):
        self._http_api_request('input/action/Play')       

    
    def play(self):
        self._play()
        
    def get_player_position(self):
        """
        Get the current videoplayer positon.
        @returns int current position, int total length
        """

        currenttime = self._http_api_request("prop/global/media/current/currenttime")
        
        if currenttime:
            duration = self._http_api_request("prop/global/media/current/metadata/duration")
            return float(currenttime.strip()), float(duration.strip())

        return None, None
    
    def set_player_position(self, position):
        """
        Currently not supported by Showtime's web interface
        Set the current videoplayer position.        
        @param position integer in seconds
        """
        
    def set_player_position_percentage(self, percentage_position):
        """
        Currently not supported by Showtime's web interface
        Set current videoplayer position, in percentage.
        
        @param percentage_position float
        """
        
    def set_start_position(self, percentage_position):
        """
        Currently not supported by Showtime's web interface
        
        @param percentage_position float
        """
