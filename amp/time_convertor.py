from datetime import datetime
import time

def convertToTime(timestamp, format):
    try:
        timeobj = datetime.strptime(timestamp, format)
    except:
        timestamp = timestamp + '.0'
        timeobj = datetime.strptime(timestamp, format)
    return timeobj

def convertToSeconds(timestamp, format='%H:%M:%S.%f'):
    """Convert timestamp to seconds if not already in seconds"""
    if ':' in timestamp:
        timeobj = convertToTime(timestamp, format)
        zerotime = convertToTime('0:00:00.000', format)
        timeinseconds = float((timeobj - zerotime).total_seconds())
    else:
        timeinseconds = float(timestamp)
    return timeinseconds

def convertSecondsToTimestamp(seconds):
    timestamp = time.strftime('%H:%M:%S', time.gmtime(seconds))
    return timestamp
