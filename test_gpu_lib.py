#!/bin/env python3
from amp.gpu import get_gpus, has_gpu, ExclusiveGPU
import logging


# test the functions
logging.basicConfig(level=logging.DEBUG)
print("get gpus", get_gpus())
print("has any gpu", has_gpu())
print("has a nvidia gpu", has_gpu('nvidia'))
print("has an amd gpu", has_gpu('amd'))
with ExclusiveGPU('nvidia') as g:
    print(f"Got an exclusive lock on {g.name}")
    lockfile = Path(g.name)
    print("lockfile exists", lockfile.exists())
    print("Attempting an exclusive lock (nested, 20s timeout)")
    try:
        with ExclusiveGPU('nvidia', timeout=20) as g1:
            print(f"Uh oh -- got an exclusive lock on the same device? {g1.name}")
    except TimeoutError:
        print("Got timeout error, which is expected")
    except Exception as e:
        print("Got an exception with nested lock")
        logging.exception(e)

print("Released main lock")
print(f"Checking lockfile existance from main lock: {g.name}", lockfile.exists())