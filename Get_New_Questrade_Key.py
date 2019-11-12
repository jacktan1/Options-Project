#https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=XBRvotvr4PJ6DIcwQgBirhltl5By0jRx0

import urllib
from questrade_api import Questrade
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='rTQA4FdripZz_-rBt8tOq_FjoYEywzOi0')
print(q.time)
