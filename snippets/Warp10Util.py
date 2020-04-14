from datetime import datetime
from datetime import timedelta
import base64

def TimeToEpoch(dt):
    dt0 = datetime.utcfromtimestamp(0)
    delta = (dt - dt0)
    return int(delta.total_seconds()  * 1000 * 1000)

def EpochToTime(epoch):
    dt0 = datetime.utcfromtimestamp(0) #datetime.strptime("1970-01-01 00:00:00.0", "%Y-%m-%d %H:%M:%S.%f")
    return dt0 + timedelta(milliseconds= (epoch / ( 1000 )))

def IsNumber(string):
    try:
        float(string)
        return True
    except Exception:
        return False;


def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')