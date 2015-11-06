__author__ = 'orion'
HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'deflate',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36 [BOT]',
}

BOT_TOKEN = '*'
OWNER = '*'
try:
    from local_settings import *
except:
    pass
