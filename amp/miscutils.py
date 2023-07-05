# misc utils that don't seem to fit anywhere else

def strtobool(string):
    "Convert a string to a boolean value"
    if string.lower() in ('y', 'yes', 'true'):
        return True
    return False


def timestamp2hhmmss(timestamp):
    "Get a unix epoch timestamp and convert it to hh:mm:ss.sss"
    hours = int(timestamp / 3600)
    timestamp -= hours * 3600
    minutes = int(timestamp / 60)
    seconds = timestamp - minutes * 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


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