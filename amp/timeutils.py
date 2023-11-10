# Utilities related to time

from datetime import datetime
from math import floor


def timestamp2hhmmss(timestamp):
    "Get a unix epoch timestamp and convert it to hh:mm:ss.sss"
    hours = int(timestamp / 3600)
    timestamp -= hours * 3600
    minutes = int(timestamp / 60)
    seconds = timestamp - minutes * 60
    return f"{hours:0d}:{minutes:02d}:{seconds:06.3f}"


def hhmmss2timestamp(hhmmss):
    "Convert hh:mm:ss.sss to timestamp"
    parts = hhmmss.split(":")
    if len(parts) == 1:
        # looks like it was just seconds
        return float(hhmmss)
    elif len(parts) == 2:
        # mm:ss
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        # hh:mm:ss
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    else:
        raise ValueError(f"Can't recognize format of {hhmmss}")


def timestampToSecond(timestamp):
    "Convert the given timestamp in the format of HH:MM:SS.fff to total seconds."
    return hhmmss2timestamp(timestamp)
    
    ts = timestamp.split(".")
    
    # no microsecond section    
    if len(ts) == 1: 
        t = datetime.strptime(timestamp, "%H:%M:%S")
    # handle microsecond
    else: 
        lms = len(ts[1])
         # strptime can handle at most 6 digits on microsecond, strip off the extra digits
        if lms > 6:
            timestamp = timestamp[:6-lms]
        t = datetime.strptime(timestamp, "%H:%M:%S.%f")
        
    delta = t - datetime(1900, 1, 1)
    second = delta.total_seconds()
    return second 


def secondToTimestamp(second): 
    "Convert the given second to timestamp in the format of HH:MM:SS.fff"
    return timestamp2hhmmss(second)

    dt = datetime.utcfromtimestamp(second)
    timestamp = dt.strftime("%H:%M:%S.%f")[:-3] 
    return timestamp


def secondToFrame(second, fps):
    "Convert the given start time in seconds (float number) to frame index based on the given frame rate."
    # BDW: use floor rather than round because we don't want to accidentally 
    # pull in a frame that's beyond the end.
    nframe = floor(second * fps)
    return nframe


def frameToSecond(nframe, fps):
    "Convert the given frame index to the start time in seconds (float number)."
    second = nframe / fps
    return second

