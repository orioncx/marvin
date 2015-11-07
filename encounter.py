# -*- encoding:utf8 -*-
__author__ = 'orion'
import time
import datetime

import requests
import pika
import json
import random
from conf import HEADERS
from lxml import html
import threading

BLOCK_MSG = u"ВНИМАНИЕ, на уровне блокировка! Вбитие через /c и ,к отключено. Используйте '/b' ',б' для бонусов или '/a' ',о' для ответа. '/s' и ',ц' без изменений"

s = requests.Session()


class LevelManager:
    def __init__(self, messenger, wather):
        self.game_started = False
        self.wather = wather
        self.game_finished = False
        self.game_active = False

        self.auto_up_time = None

        self.current_level_num = 0
        self.unclosed_sect_count = 1
        self.input_blocked = False
        self.closed_sectors = []
        self.closed_bonuses = []
        self.opened_penalty_hints = []
        self.level_id = None
        self.level_num = None

        self.task = ''
        self.hints = ''
        self.penalty_hints = ''
        self.messenger = messenger
        self.blockage = False

    def set_level(self, lid, lnum, task, hints, opened_penalty_hints, closed_bonuses, closed_sectors,
                         unclosed_sect_count, answ_en, all_timers, up_time_seconds, blockage):
        if lid and lnum:
            if self.level_id != lid:
                started=False
                if self.level_id:
                    started=True
                self.game_started = True
                self.game_active = True
                self.level_id = lid
                self.level_num = lnum
                if started:
                    self._send_msg(u'АП')
                self._send_msg(task)
                self.blockage = blockage
                if blockage:
                    self._send_msg(BLOCK_MSG)
                self.messenger.clear_photo_storage()
                self.messenger.clear_storage()
                self.wather.clear_queue()
                return


        if not answ_en:
            self.input_blocked = True
        else:
            self.input_blocked = False
            self.wather.proc_queue()

            # up proc
        if len(self.hints) < len(hints):
            new_hints = hints[len(self.hints):]
            for hint in new_hints:
                self._send_msg(u"Подсказка:\n%s" % hint)
        self.hints = hints
        self.up_time_seconds = up_time_seconds
        self.opened_penalty_hints = opened_penalty_hints
        self.closed_bonuses = closed_bonuses
        self.closed_sectors = closed_sectors
        self.unclosed_sect_count = unclosed_sect_count
        self.all_timers = all_timers
        self.input_blocked = not answ_en


        self.task = task
        if not self.game_started:
            self.game_started = True
            self.game_active = True

    def get_level_id(self):
        return self.level_id

    def get_level_num(self):
        return self.level_num

    def _send_msg(self, msg, chat_id=None):
        if self.messenger:
            self.messenger.send_message(msg, chat_id)
        else:
            print(msg)


class EnWatcher:
    def __init__(self, auth_params, messenger):
        self.s = requests.Session()
        self.l = LevelManager(messenger, self)
        self.messenger = messenger
        self.auth_params = auth_params
        self.active = True
        self.refresher_enabled = False
        self.queue = []

    def clear_queue(self):
        self.queue = []

    def proc_queue(self):
        if len(self.queue) and not self.l.input_blocked:
            answr_to_inp = self.queue[0]
            self.queue = self.queue[1:]
            self.input_answer(answr_to_inp, from_queue=True)

    def _login(self):
        host = "".join(['http://%s/Login.aspx' % self.auth_params['domain'], '?return=%2fDefault.aspx&lang=ru'])
        ddlNetwork = 1
        if self.auth_params['domain'].find("quest.ua") != -1:  # not sure that is that required
            ddlNetwork = 2
        post_data = {'Login': '%s' % self.auth_params['login'],
                     'password': '%s' % self.auth_params['password'],
                     'ddlNetwork': ddlNetwork,  # not sure that is that required
                     'btnLogin': 0}
        r = self.s.post(host, data=post_data, headers=HEADERS)
        if len(r.history) == 2:
            return True
        else:
            return False

    def _humanize_task(self, task_p):
        task_html = html.tostring(task_p)
        task_html = task_html.replace('<br>', '\n').replace('<br\>', '\n').replace('<BR\>', '\n').replace('<BR>', '\n')
        task_html = task_html.replace('<strong>', '*').replace('</strong>', '*').replace('</b>', '*').replace('<b>',
                                                                                                              '*').replace(
            '</B>', '*').replace('<B>', '*')
        task_html = task_html.replace('<em>', '_').replace('</em>', '_').replace('<i>', '_').replace('</i>',
                                                                                                     '_').replace(
            '</I>', '_').replace('<I>', '_')

        imgs = task_p.cssselect('img')
        for img in imgs:
            task_html = task_html.replace(html.tostring(img), img.attrib['src'].replace('*','\*').replace('_','\_'))
        links = task_p.cssselect('a')
        for link in links:
            task_html = task_html.replace(html.tostring(link), '(%s[link](%s))' % (link.text, link.attrib['href'].replace('*','\*').replace('_','\_')))

        final_task = html.fromstring(task_html).text_content()
        return final_task

    def input_answer(self, answer, relogin=False, check_block=False, from_queue = False):
        print(answer,from_queue)
        if not self.l.game_active:
            return {'success': False, 'correct': False, 'msg': u'Игра неактивна'}
        if check_block:
            if self.l.blockage:
                self.messenger.send_message(BLOCK_MSG)
                return
        if self.l.input_blocked:
            self.messenger.send_message(u'"%s"??? - Ввод заблокирован. Подождите. Вобью при первой возможности.' % answer)
            self.queue.append(answer)
            return
        r = self.s.post('http://%s/gameengines/encounter/play/%s/?rnd=%s' % (
            self.auth_params['domain'], self.auth_params['gameid'], random.random()),
                        data={'LevelId': self.l.get_level_id(),
                              'LevelNumber': self.l.get_level_num(),
                              'LevelAction.Answer': answer},
                        headers=HEADERS)

        if r.text.find('loginEn') != -1:
            if not relogin:
                self._login()
                return self.input_answer(answer, relogin=True, check_block=check_block, from_queue=from_queue)
            else:
                self.messenger.send_message_to_owner('Code input error - please check')
                return
        if r.text.find('color_incorrect') != -1:
            if from_queue:
                print(u'Из очереди: "%s"-'%answer)
                self.messenger.send_message(u'Из очереди: "%s"-'%answer)
            return {'success': True, 'correct': False, 'msg': u''}

        elif r.text[:r.text.find('jspVerticalBar')].find('color_correct') != -1:
            if from_queue:
                print('Из очереди: "%s"-'%answer)
                self.messenger.send_message(u'Из очереди: "%s"+'%answer)
            return {'success': True, 'correct': True, 'msg': u''}
        return None

    def input_bonus_answer(self, answer):
        if not self.l.game_active:
            return {'success': False, 'correct': False, 'msg': u'Игра неактивна'}
        r = self.s.post('http://%s/gameengines/encounter/play/%s/?rnd=%s' % (
            self.auth_params['domain'], self.auth_params['gameid'], random.random()),
                        data={'LevelId': self.l.get_level_id(),
                              'LevelNumber': self.l.get_level_num(),
                              'BonusAction.Answer': answer},
                        headers=HEADERS)
        if r.text.find('color_incorrect') != -1:
            return {'success': True, 'correct': False, 'msg': u''}
        elif r.text[:r.text.find('jspVerticalBar')].find('color_correct') != -1:
            return {'success': True, 'correct': True, 'msg': u''}
        return None

    def game_refresh(self, relogin=False):

        r = self.s.get('http://%s/gameengines/encounter/play/%s/?rnd=%s' % (
            self.auth_params['domain'], self.auth_params['gameid'], random.random()), headers=HEADERS)


        if r.text.find('Panel_lblGameError') != -1:
            print('game still not started or bot not included in team')
            return True
        if r.text.find('Panel_TimerHolder') != -1:
            print('game countdown')
            return True


        page = html.fromstring(r.text)
        if len(page.cssselect('#loginEn')):
            if not relogin:
                self._login()
                return self.game_refresh(relogin=True)
            else:
                self.messenger.send_message_to_owner('Login error - please check')
                return
        lid, lnum = None,None
        try:
            lid = page.xpath('//input[@type="hidden"][@name="LevelId"]/@value')[0]
            lnum = page.xpath('//input[@type="hidden"][@name="LevelNumber"]/@value')[0]
        except IndexError:
            self.l.input_blocked = True

        blockage = len(page.cssselect('.blockageinfo'))

        sectors_cont = page.cssselect('.cols-wrapper')

        headers = page.cssselect('h3:not(.timer)')
        closed_sectors = []
        unclosed_sect_count = 1

        if len(sectors_cont):
            sectors_header = headers[0]
            headers = headers[1:]
            for sector in sectors_cont[0].cssselect('.color_correct'):
                closed_sectors.append(sector.text_content())
            unclosed_sect_text = sectors_header.text_content()
            if u'закрыть' in unclosed_sect_text:
                unclosed_sect_count = int(unclosed_sect_text[unclosed_sect_text.rfind(' ') + 1:unclosed_sect_text.rfind(')')])
            else:
                unclosed_sect_count = int(unclosed_sect_text.replace(u'На уровне ', '')[
                                          :unclosed_sect_text.replace(u'На уровне ', '').find(' ')])
        open_bonus_headers = page.cssselect('h3.color_bonus')
        closed_bonus_headers = page.cssselect('h3.color_correct')
        penalty_hint_headers = page.cssselect('h3.inline')
        task = self._humanize_task(headers[0].getnext())
        hints = [self._humanize_task(header.getnext()) for header in headers[1:] if
                 header not in open_bonus_headers
                 and header not in closed_bonus_headers
                 and header not in penalty_hint_headers
                 and html.tostring(
                     header.getnext()).strip() != '<p></p>']
        opened_penalty_hints = [self._humanize_task(penalty_hint_header.getnext()) for penalty_hint_header in
                                penalty_hint_headers if
                                '/gameengines/encounter/play/' not in html.tostring(penalty_hint_header.getnext())]
        closed_bonuses = [self._humanize_task(closed_bonus_header.getnext()) for closed_bonus_header in
                          closed_bonus_headers]
        all_timers = [i.getparent().text_content()[:i.getparent().text_content().find('//<![CDATA[')].strip()
                      for i in page.cssselect('span.bold_off')]
        up_time_seconds = None
        up_time_c = page.cssselect('h3.timer')
        if len(up_time_c):
            timer_html = html.tostring(up_time_c[0])
            st_p = timer_html.find('StartCounter') + 14
            up_time_seconds = int(timer_html[st_p:st_p + timer_html[st_p:].find(',')])

        answ_en = len(page.cssselect('#Answer'))
        self.l.set_level(lid, lnum, task, hints, opened_penalty_hints, closed_bonuses, closed_sectors,
                         unclosed_sect_count, answ_en, all_timers, up_time_seconds, blockage)

        return False

    def shutdown(self):
        self.active = False

    def refresher(self):
        while self.refresher_enabled:
            try:
                self.game_refresh()
            except Exception as e:
                print(e.message)
            time.sleep(0.5)

    def start_refresher(self):
        self.refresher_enabled = True
        self.refresher = threading.Thread(target=self.refresher)
        self.refresher.start()

if __name__ == '__main__':
    def load_params():
        f = open('config.conf', 'r+b')
        data = json.loads(f.read())
        f.close()
        return data
    en = EnWatcher(load_params(),None)
    en._login()
    en.start_refresher()