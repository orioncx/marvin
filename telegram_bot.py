# -*- encoding:utf8 -*-
import time
from encounter import EnWatcher
import json
import telegram
import threading
from conf import BOT_TOKEN, OWNER
from telegram.error import TelegramError


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
        self.photo_storage = []

    def add_to_storage(self,u):
        if self.logined and self.chat_id:
            self.storage.append(u.message)

    def add_to_photo_storage(self,u):
        if self.logined and self.chat_id:
            self.photo_storage.append(u.message)

    def get_storage(self):
        if self.logined and self.chat_id:
            for message in self.storage:
                self.bot.forwardMessage(self.chat_id, message.chat_id, message.message_id)

    def get_photo_storage(self):
        if self.logined and self.chat_id:
            for message in self.photo_storage:
                self.bot.forwardMessage(self.chat_id, message.chat_id, message.message_id)

    def send_message_to_owner(self, msg):
        if msg and self.owner_id:
            self.send_message(msg, self.owner_id)

    def send_message(self, msg, chat_id=None):
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
        self.last_update_id = msg.update_id

        if text.startswith(u'/') or text.startswith(u',') or text.startswith(u'.'):
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

        if text.startswith(u'/stop'):
            if user_sent == OWNER:
                self.send_message_to_owner(u'Отключаю слежение')
                self.en_watcher.shutdown()
                time.sleep(5)
                self.chat_id = None
                self.en_watcher = None
                self.send_message_to_owner(u'Отключил слежение')
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)
            return

        if text.startswith(u'/sleep'):
            if user_sent == OWNER:
                self.upd_interval = 20
                self.send_message(u'Замедляю интервал опроса до 20 сек.', chat_id)
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)
            return

        if text.startswith(u'/run'):
            if user_sent == OWNER:
                self.upd_interval = 0.01
                self.send_message(u'Ускоряю интервал опроса до 0.01 сек.', chat_id)
            else:
                self.send_message(u'Несоответствие уровня доступа.', chat_id)
            return

        if text.startswith(u'/clearqueue'):
            if self.logined and chat_id == self.chat_id:
                self.en_watcher.clear_queue()
                self.send_message(u'Очередь вбития очищена.')
            return

        if text.startswith(u'/memory'):
            if self.logined and self.chat_id:
                if len(self.storage):
                    self.get_storage()
                else:
                    self.send_message(u'Ничего не помню')
            return

        if text.startswith(u'/photos'):
            if self.logined and self.chat_id:
                if len(self.storage):
                    self.get_photo_storage()
                else:
                    self.send_message(u'Нет фоток на этом уровне')
            return

        if text.startswith(u'/help'):
            if self.logined and self.chat_id:
                self.send_message(u'\'/c\' или \',\' - вбитие кода\n'+\
                                  u'\'/b\' или \'.\' - вбитие бонуса на уровне с блокировкой\n'+\
                                  u'\'/s\' или \',п\' - вбитие кода с пробелами\n'+\
                                  u'\'/r\' или \',з\' - запомнить текст сообщения до конца уровня\n'+\
                                  u'пробел между командой и аргументом не обязателен'
                                  )
            return

        if text.startswith(u'/task'):
            if self.logined and self.chat_id:
                self.send_message(self.en_watcher.l.task)
            return

        if text.startswith(u'/timers'):
            if self.logined and self.chat_id:
                if len(self.en_watcher.l.all_timers):
                    r = '\n'.join(self.en_watcher.l.all_timers)
                else:
                    r=u'На уровне нет ни одного отсчета.'
                self.send_message(r)

            return



        if text.startswith(u'/hints'):
            if self.logined and self.chat_id:
                if len(self.en_watcher.l.hints) or len(self.en_watcher.l.opened_penalty_hints):
                    r = '\n'.join(self.en_watcher.l.hints)
                    if r:
                        r += '\n'
                    r += '\n'.join(self.en_watcher.l.opened_penalty_hints)
                else:
                    r = u'На уровне нет открытых подсказок.'
                self.send_message(r)
            return

        if text.startswith(u'/bonuses'):
            if self.logined and self.chat_id:
                if len(self.en_watcher.l.closed_bonuses):
                    r = '\n'.join(self.en_watcher.l.closed_bonuses)
                else:
                    r = u'На уровне нет открытых бонусов.'
                self.send_message(r)
            return

        if text.startswith(u'/s') or text.startswith(u',п') or text.startswith(u', п'):
            if self.logined and chat_id == self.chat_id:
                try:
                    raw_text = text.replace(u'/s', '').replace(u',п', '').replace(u', п', '').strip()
                    lr = self.en_watcher.input_answer(raw_text)
                    if lr and lr['success']:
                        self.send_message('"%s"%s ' % (raw_text, '+' if lr['correct'] else '-'))
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))
            return

        if text.startswith(u'/b') or text.startswith(u'.'):
            if self.logined and chat_id == self.chat_id:
                try:
                    if text.startswith(u'/b') or text.startswith(u'/б'):
                        raw_text = text[2:].strip()
                    else:
                        raw_text = text[1:].strip()
                    lr = self.en_watcher.input_bonus_answer(raw_text)
                    if lr and lr['success']:
                        self.send_message('"%s"%s ' % (raw_text, '+' if lr['correct'] else '-'))
                except Exception as e:
                    self.send_message_to_owner('Error code input %s %s' % (e.message,text))
            return

        if text.startswith(u'/r') or text.startswith(u',з') or text.startswith(u', з'):
            if msg:
                self.add_to_storage(msg)
            return


        if text.startswith(u'/c') or text.startswith(u'/с') or text.startswith(u','):
            if self.logined and chat_id == self.chat_id:
                try:
                    if text.startswith(u'/c') or text.startswith(u'/с'):
                        raw_text = text[2:].strip()
                    else:
                        raw_text = text[1:].strip()
                    answers = raw_text.split(' ')
                    result_str = ''
                    for a in answers:
                        if a.lower() in self.en_watcher.l.closed_sectors:
                            result_str += u'"%s" %s' % (a, '\[:||||:]')
                        else:
                            lr = self.en_watcher.input_answer(a, check_block=False)
                            if lr and lr['success']:
                                result_str += u'"%s"%s ' % (a, '+' if lr['correct'] else '-')
                    self.send_message(result_str)
                except Exception as e:
                    self.send_message_to_owner(u'Error code input %s %s' % (e.message,text))
            return


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
