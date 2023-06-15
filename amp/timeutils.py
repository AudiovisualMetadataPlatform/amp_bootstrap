# Utilities related to time

from datetime import datetime
from math import floor


def timestampToSecond(timestamp):
    "Convert the given timestamp in the format of HH:MM:SS.fff to total seconds."
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

