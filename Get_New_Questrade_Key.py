# https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=0VBibp9obFMdrjScVM0BGp8HO-q8cLRP0

import urllib
from questrade_api import Questrade
import os
import ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='MZdQ_QGuY2Ul8FrQiTeGpYgxnyZAez9L0')
print(q.time)
