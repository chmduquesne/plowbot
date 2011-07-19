from jabberbot import JabberBot
import threading
import time
import os

class PlowBot(JabberBot):

    def __init__(self, jid, password, res = None):
        super(PlowBot, self).__init__(jid, password, res)
        self.loop_killed = False
        self.download_queue = []
        self.log_queue = []
        self.users = []

    def idle_proc(self):
        if not self.log_queue:
            return
        messages = self.log_queue
        self.log_queue = []
        for message in messages:
            for user in self.users:
                self.send(user, message)

    def unknown_command(self, mess, cmd, arg):
        user = mess.getFrom()
        if not user in self.users:
            self.users.append(user)
        for url in (' '.join([cmd, arg])).split(' '):
            self.download_queue.append(url)
        return "downloading..."

    def download_loop(self):
        while not self.loop_killed:
            time.sleep(1)
            if self.download_queue:
                d = self.download_queue.pop()
                msg = os.popen("plowdown %s" % d).read()
                self.log_queue.append(msg)
                if self.loop_killed:
                    return

username = 'xxxx'
password = 'xxxx'

if __name__ == "__main__":
    bot = PlowBot(username,password)
    th = threading.Thread(target = bot.download_loop)
    bot.serve_forever(connect_callback = lambda: th.start())

