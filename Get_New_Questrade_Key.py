#https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=agwa8zU40zyuPu7unHJfECMPRwDdTQPE0

import urllib
from questrade_api import Questrade
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='5byi3psARx_E0kVYL38hbB8XMIX0GKji0')
print(q.time)
