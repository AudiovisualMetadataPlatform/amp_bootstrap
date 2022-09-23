# misc utils that don't seem to fit anywhere else

def strtobool(string):
    "Convert a string to a boolean value"
    if string.lower() in ('y', 'yes', 'true'):
        return True
    elif string.lower() in ('n', 'no', 'false'):
        return False