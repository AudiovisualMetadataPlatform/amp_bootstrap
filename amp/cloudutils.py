import platform
import hashlib

def generate_persistent_name(prefix, *data):
    "Generate a persistent name from the prefix and data"
    #ok_chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    name = prefix + "-" + platform.node().split('.')[0] + '-'
    #parts = []
    #for p in data:
    #    part = ''.join(x if x in ok_chars else '_' for x in str(p))
    #    parts.append(part)
    #name += "-".join(parts)
    return name + "-" + hashlib.md5('_'.join([str(x) for x in data]).encode()).hexdigest()
    


