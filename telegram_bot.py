# -*- encoding:utf8 -*-
import time
from encounter import EnWatcher

__author__ = 'orion'
import pika
import json
import telegram
import threading
from conf import BOT_TOKEN, CHAT_ID, OWNER




# connection = pika.BlockingConnection(pika.ConnectionParameters(
#         host='localhost'))
# channel = connection.channel()
# channel.queue_declare(queue='hello')
# channel.basic_publish(exchange='',
#                       routing_key='hello',
#                       body='syhsdfsdgjsdgj')

# set username password game_id
# start chat_id***
# run game
# change upd speed

# uptime input_code timers hints


def save_params(params):
    data = json.dumps(params)
    f = open('config.conf', 'w+b')
    f.write(data)
    f.close()


def load_params():
    f = open('config.conf', 'r+b')
    data = json.loads(f.read())
    f.close()
    return data



class Messenger:
    commands = {
        '/init': '',
        '/update': '',
        '/help': '',
        '/set': '',
        '/c': '',
        '/b': '',
        '/a': '',
        '/timers': '',
        '/hints': '',
        '/startgame': '',
        '/stopgame': '',
    }

    def __init__(self):
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.chat_id = CHAT_ID
        self.upd_interval = 0.1
        self.last_update_id = None
        self.game_params = load_params()
        self.logined = False

        self.en_watcher = None

        self._run_updater()

    def send_message(self, msg, chat_id=None):
        if msg:
            print(msg)
            print(self.chat_id)
            print(chat_id)
            self.bot.sendMessage(chat_id=chat_id or self.chat_id, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)

    def set(self, text, chat_id):
        if len(text.split(' '))!=2:
            self.send_message(u'choices: %s' % ', '.join(self.game_params.iterkeys()), chat_id)
            self.send_message(u'/config key value', chat_id)
            return
        name, value = text.split(' ')[:2]
        if name.lower() in self.game_params.iterkeys():
            self.game_params[name.lower()] = value
            save_params(self.game_params)
            self.send_message(u'%s set to %s' % (name, value), chat_id)
        else:
            self.send_message(u'choices: %s' % ', '.join(self.game_params.iterkeys()), chat_id)

    def proc_msg(self, msg):
        user_sent = msg.message.from_user.username
        text = msg.message.text
        chat_id = msg.message.chat_id

        if text.startswith(u'/config'):
            if user_sent == OWNER:
                if ' ' in text:
                    self.set(text.replace(u'/config', u'').strip(), chat_id)
                else:
                    if self.chat_id != chat_id:
                        self.send_message(self.game_params, chat_id)
            else:
                self.send_message(u'Forbidden', chat_id)

        if text.startswith(u'/login'):
            self.en_watcher = EnWatcher(self.game_params, self)
            self.logined = self.en_watcher._login()
            if self.logined:
                self.send_message(u'Successfully logined', chat_id)
            else:
                self.send_message(u'Log in Fail =( check params', chat_id)

        if text.startswith(u'/init'):
            if user_sent == OWNER:
                if self.logined:
                    self.chat_id = chat_id
                    self.send_message(u'Слежение запущено.')
                    self.en_watcher.start_refresher()

                else:
                    self.send_message(u'Сначала авторизация', chat_id)
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)

        if text.startswith(u'/c') or text.startswith(u'/с'):
            raw_text = text.replace(u'/c', '').replace(u'/с', '').strip()
            answers = raw_text.split(' ')
            result_str=''
            for a in answers:
                lr = self.en_watcher.input_answer(a)
                if lr and lr['success']:
                    result_str += '"%s"%s ' % (a, '+' if lr['correct'] else '-')
                self.send_message(result_str)

        print(user_sent)
        # self.chat_id=msg.message.chat_id
        self.last_update_id = msg.update_id
        # self.send_message(msg.message.text)

    def _run_updater(self):
        self.updater_enabled = True
        self.updater = threading.Thread(target=self.get_messages)
        self.updater.run()

    def _stop_updater(self):
        self.updater_enabled = False

    def get_messages(self):
        while self.updater_enabled:
            time.sleep(self.upd_interval)
            updates = self.bot.getUpdates(limit=10, offset=self.last_update_id + 1 if self.last_update_id else None)
            if len(updates):
                for u in updates:
                    self.proc_msg(u)


if __name__ == '__main__':
    m = Messenger()
