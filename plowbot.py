#!/usr/bin/env python2
#
# PlowBot: A bot that downloads the links you paste using plowshare.
#
# Copyright (c) 2011 Christophe-Marie Duquesne <chm.duquesne@gmail.com>
#
# This program is licensed under the terms WTF Public License, in case
# anybody cares.
#
# You should have received (or not) a copy of the WTFPL along with this
# program. If not, see <http://sam.zoy.org/wtfpl/COPYING>.

from __future__ import with_statement
from jabberbot import JabberBot
from xdg.BaseDirectory import save_config_path, save_data_path
import os.path
import threading
import time
import subprocess
import json
import readline
import logging
import logging.handlers

class PlowBot(JabberBot):

    def __init__(self, user, password, max_parallel_downloads=3,
            download_directory = "~/downloads", res = None):
        super(PlowBot, self).__init__(user, password, res)
        self.download_queue = []
        self.queue_sema = threading.Semaphore(0) # == len(download_queue)
        self.parallel_downloads_sema = threading.BoundedSemaphore(
                max_parallel_downloads)
        self.download_directory = os.path.expanduser(download_directory)
        assert os.path.exists(self.download_directory), "Download directory does not exist"
        # logging stuff - newer versions of jabberbot
        if not callable(self.log):
            logfile = os.path.join(save_data_path("plowbot"), "plowbot.log")
            handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=100000)
            formatter = logging.Formatter("%(asctime) - %(name)s - %(levelname)s - %(message)s")
            self.log.addHandler(handler)
            self.log.setLevel(logging.INFO)

    # We do not want a command for downloading urls: we prefer every
    # message to be treated as a set of urls we'll try to download. Thus,
    # we use a "trick": we use the unknown_command method for that.
    def unknown_command(self, msg, cmd, arg):
        """Splits the input and adds it to the download queue"""
        for url in (' '.join([cmd, arg])).split():
            self.download_queue.append((msg, url))
            self.queue_sema.release()
        return "Launching download(s)."

    def download_loop(self):
        """Loops on downloading files of the queue."""
        while True:
            self.queue_sema.acquire() # wait until the queue is not empty
            msg, url = self. download_queue.pop()
            t = threading.Thread(target = self.do_download, args = (msg,
                url))
            t.daemon = True
            t.start()

    def do_download(self, msg, url):
        """Downloads the given url and replies when finished"""
        with self.parallel_downloads_sema:
            p = subprocess.Popen(["plowdown", "-o",
                self.download_directory, url],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
            p.wait()
            stdout, stderr = p.communicate()
            if p.returncode != 0 or not stdout:
                reply = "Error: " + stderr
                reply += "Are you sure you pasted a valid link?"
            else:
                reply = stdout.strip() + " successfully downloaded."
            self.send_simple_reply(msg, reply)

def make_new_config(config_path):
    import getpass
    user = raw_input("Please enter the Jabber ID for your bot: ")
    while True:
        attempt1 = getpass.getpass("Please enter the Jabber password: ")
        attempt2 = getpass.getpass("Please confirm the Jabber password: ")
        if (attempt1 == attempt2):
            password = attempt1
            break
    dl_dir = raw_input("Please enter your download directory: ")
    with open(config_path, "wb") as f:
        json.dump({
            "user": user,
            "password": password,
            "max_parallel_downloads": 3,
            "download_directory": dl_dir
            }, indent = 4, fp = f)
    print("config saved in %s" % config_path)

if __name__ == "__main__":
    config_path = os.path.join(save_config_path("plowbot"), "plowbotrc")
    if not os.path.exists(config_path):
        make_new_config(config_path)
    with open(config_path) as f:
        config = json.load(f)
        bot = PlowBot(**config)
        t = threading.Thread(target = bot.download_loop)
        t.daemon = True
        bot.serve_forever(connect_callback = lambda: t.start())
