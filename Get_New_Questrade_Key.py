# https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=4-_a9tEBt5JhA-RhrhlTMgDsw4Qctdlg0

import urllib
from questrade_api import Questrade
import os
import ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context
q = Questrade(refresh_token='7PG99-F0DeN2zjvVAEmGR-35O-DwvODV0')
print(q.time)
