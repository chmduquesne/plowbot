# !/usr/bin/env python
#
# PlowBot: A bot that dowloads the links you paste using plowshare.
# Copyright (c) 2011 Christophe-Marie Duquesne <chm.duquesne@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement
from jabberbot import JabberBot
import sys
import getopt
import threading
import time
import subprocess

class PlowBot(JabberBot):

    def __init__(self, jid, password, max_parallel_downloads=3,
            res = None):
        super(PlowBot, self).__init__(jid, password, res)
        self.download_queue = []
        self.parallel_downloads_sema = threading.BoundedSemaphore(
                max_parallel_downloads)
        self.queue_sema = threading.Semaphore(0)

    # We do not want a command for downloading urls: we want every message
    # to be treated as a set of urls we'll try to download. Thus, we use a
    # "trick": we use the unknown_command method for that.
    def unknown_command(self, mess, cmd, arg):
        """Splits the input and adds it to the download queue"""
        for url in (' '.join([cmd, arg])).split():
            self.download_queue.append((mess, url))
            self.queue_sema.release() # release as many times as
        return "Launching download(s)."

    def download_loop(self):
        """Loops on downloading files of the queue."""
        while True:
            self.queue_sema.acquire() # wait until the queue is not empty
            mess, url = self. download_queue.pop()
            t = threading.Thread(target = self.do_download, args = (mess,
                url))
            t.daemon = True
            t.start()

    def do_download(self, mess, url):
        """Downloads the given url and replies when finished"""
        with self.parallel_downloads_sema:
            p = subprocess.Popen(["plowdown", url],
                    stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            p.wait()
            stdout, stderr = p.communicate()
            if p.returncode != 0 or not stdout:
                reply = "Are you sure you pasted a valid link? "
                reply += "Error: " + stderr.strip()
            else:
                reply = stdout.strip() + " successfully downloaded."
            self.send_simple_reply(mess, reply)

if __name__ == "__main__":
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "hu:p:", ["help",
            "user=", "password="])
    except getopt.GetoptError, err:
        print str(err)
        print __doc__
        sys.exit(2)
    output = None
    verbose = False
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
        elif opt in ("-u", "--user"):
            user = arg
        elif opt in ("-p", "--password"):
            password = arg
        else:
            assert False, "unhandled option"
    if not (user and password):
        print("missing identifiers")
        print(__doc__)

    bot = PlowBot(user, password)
    t = threading.Thread(target = bot.download_loop)
    t.daemon = True
    bot.serve_forever(connect_callback = lambda: t.start())

