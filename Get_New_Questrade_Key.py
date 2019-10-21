#https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=5P0IIBuxALGaHQrNud02g3YD2a_zYlbF0

import urllib
from questrade_api import Questrade
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='5DVH1vbXCuSmXhoIFQFqWYkAAZpY0w0X0')
print(q.time)
