# -*- encoding:utf8 -*-
import time
from encounter import EnWatcher

__author__ = 'orion'
import pika
import json
import telegram
import threading
from conf import BOT_TOKEN, OWNER
from telegram.error import TelegramError




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
        self.chat_id = None
        self.owner_id=None
        self.upd_interval = 0.1
        self.last_update_id = None
        self.game_params = load_params()
        self.logined = False

        self.en_watcher = None

        self._run_updater()

        self.storage=[]
        self.photo_storage=[]

    def clear_storage(self):
        self.storage = []

    def clear_photo_storage(self):
        self.storage = []

    def add_to_storage(self,u):
        if self.logined and self.chat_id:
            self.storage.append(u.message)

    def add_to_photo_storage(self,u):
        if self.logined and self.chat_id:
            self.storage.append(u.message)

    def get_storage(self):
        if self.logined and self.chat_id:
            for message in self.storage:
                self.bot.forwardMessage(self.chat_id, message.chat_id, message.message_id)

    def get_photo_storage(self):
        if self.logined and self.chat_id:
            for message in self.storage:
                self.bot.forwardMessage(self.chat_id, message.chat_id, message.message_id)

    def send_message_to_owner(self, msg):
        if msg and self.owner_id:
            self.send_message(msg, self.owner_id)

    def send_message(self, msg, chat_id=None):
        print(msg)
        try:
            if msg:
                self.bot.sendMessage(chat_id=chat_id or self.chat_id, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
        except TelegramError:
            if msg:
                try:
                    self.bot.sendMessage(chat_id=chat_id or self.chat_id, text=msg)
                except:
                    self.send_message_to_owner(u'cant send message')

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

        if text.startswith(u'/') or text.startswith(u','):
            pass
        else:
            if msg.message.photo:
                self.add_to_photo_storage(msg)
            else:
                return

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
            if user_sent == OWNER:
                self.owner_id = chat_id
                self.en_watcher = EnWatcher(self.game_params, self)
                self.logined = self.en_watcher._login()
                if self.logined:
                    self.send_message(u'Successfully logined', chat_id)
                else:
                    self.send_message(u'Log in Fail =( check params', chat_id)
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)

        if text.startswith(u'/init'):
            if user_sent == OWNER:
                if self.logined:
                    self.chat_id = chat_id
                    self.en_watcher.start_refresher()
                    self.send_message(u'Слежение запущено.')
                else:
                    self.send_message(u'Сначала авторизация', chat_id)
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)

        if text.startswith(u'/clearqueue'):
            if self.logined and chat_id == self.chat_id:
                self.en_watcher.clear_queue()
                self.send_message(u'Очередь вбития очищена.')
            return

        if text.startswith(u'/c') or text.startswith(u'/с') or text.startswith(u',к'):
            if self.logined and chat_id == self.chat_id:
                try:
                    raw_text = text.replace(u'/c', '').replace(u'/с', '').replace(u',к', '').strip()
                    answers = raw_text.split(' ')
                    result_str = ''
                    for a in answers:
                        print(a)
                        lr = self.en_watcher.input_answer(a, check_block=True)
                        if lr and lr['success']:
                            result_str += '"%s"%s ' % (a, '+' if lr['correct'] else '-')
                    self.send_message(result_str)
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))

        if text.startswith(u'/a') or text.startswith(u'/а') or text.startswith(u',о'):
            if self.logined and chat_id == self.chat_id:
                try:
                    raw_text = text.replace(u'/a', '').replace(u'/а', '').replace(u',о', '').strip()
                    answers = raw_text.split(' ')
                    result_str = ''
                    for a in answers:
                        print(a)
                        lr = self.en_watcher.input_answer(a)
                        if lr and lr['success']:
                            result_str += '"%s"%s ' % (a, '+' if lr['correct'] else '-')
                    self.send_message(result_str)
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))

        if text.startswith(u'/s') or text.startswith(u',п'):
            if self.logined and chat_id == self.chat_id:
                try:
                    raw_text = text.replace(u'/s', '').replace(u',п', '').strip()
                    lr = self.en_watcher.input_answer(raw_text)
                    if lr and lr['success']:
                        self.send_message('"%s"%s ' % (raw_text, '+' if lr['correct'] else '-'))
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))

        if text.startswith(u'/b') or text.startswith(u',б'):
            if self.logined and chat_id == self.chat_id:
                try:
                    raw_text = text.replace(u'/b', '').replace(u',б', '').strip()
                    lr = self.en_watcher.input_bonus_answer(raw_text)
                    if lr and lr['success']:
                        self.send_message('"%s"%s ' % (raw_text, '+' if lr['correct'] else '-'))
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))

        if text.startswith(u'/r') or text.startswith(u',з'):
            self.add_to_storage(msg)

        if text.startswith(u'/memory'):
            if self.logined and self.chat_id:
                if len(self.storage):
                    self.get_storage()
                else:
                    self.send_message(u'Ничего не помню')

        if text.startswith(u'/photos'):
            if self.logined and self.chat_id:
                if len(self.storage):
                    self.get_storage()
                else:
                    self.send_message(u'Нет фоток на этом уровне')

        print(user_sent)
        # self.chat_id=msg.message.chat_id
        self.last_update_id = msg.update_id
        # self.send_message(msg.message.text)

    def _run_updater(self):
        self.updater_enabled = True
        self.updater = threading.Thread(target=self.get_messages)
        self.updater.start()

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
