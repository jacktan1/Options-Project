# https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=ALqC5utsCSqypFms2i2TKw3kYw1OYc8u0

import urllib
from questrade_api import Questrade
import os
import ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='3BgnSsfk4ABmmpNo_TbvQ3Z76ZzPFgA60')
print(q.time)
