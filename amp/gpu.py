# Utilities for detecting/using a GPU

import shutil
from pathlib import Path
import time
import os
import logging


def get_gpus():
    "Return a dict of GPU types and devices"
    devs = {}
    if shutil.which("nvidia-smi") is not None:
        for dev in Path("/dev").glob("nvidia[0-9]"):
            if 'nvidia' not in devs:
                devs['nvidia'] = []
            devs['nvidia'].append(str(dev.absolute()))
    # TODO: there should be checks for AMD and Intel GPUs
    return devs


def has_gpu(vendor: None):
    "Determine if a GPU (of an optional vendor) is on this system"
    devs = get_gpus()
    if vendor:
        return vendor in devs
    else:
        return len(devs) > 0
    

class ExclusiveGPU:
    def __init__(self, vendor, device=None, timeout=60*60*24*365, period=10):
        """Wait for exclusive access to a GPU device.  if the device is none 
           then the first available will be used.  The name can be found
           via the .name property"""
        gpus = get_gpus()
        if vendor not in gpus:
            raise ModuleNotFoundError(f"There are no gpus with vendor {vendor}")
        
        if device is None:
            # determine if there's a free device.  
            # TODO: pick a free device.  in the mean time we're just going to pick the first device.
            device = gpus[vendor][0]
        elif device not in gpus[vendor]:
            raise FileNotFoundError(f"No GPU with device name {device}")
        
        device = Path(device)
        if not device.exists():
            raise FileNotFoundError(f"GPU device at {device!s} doesn't exist")                
        self.lockfile = Path("/tmp", "gpu-" + device.name + ".lock")
        self.timeout = timeout
        self.period = period
        self.name = device


    def __enter__(self):        
        timeout = time.time() + self.timeout()
        while time.time() < timeout:
            try:
                logging.debug(f"Attempting to lock {self.lockfile!s}")
                fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                os.close(fd)
                logging.debug("Lock successful")
            except Exception:
                logging.debug(f"Can't lock.  Waiting for {self.period} seconds")
                time.sleep(self.period)
        else:
            # we didn't break out of the loop -- so we timed out
            raise TimeoutError(f"GPU never became available in {self.timeout} seconds")


    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.lockfile.exists():
            self.lockfile.unlink()




    