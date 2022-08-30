"""
Setup the environment for subprocesses

Make sure that this library is in the PYTHONPATH, and make sure that any "expected to be there"
things are also in the path.

This should really only be used by amp_control.py and amp_devel.py since the paths
that are generated are relative to the script and those are the only ones in the
right place.

"""

import os
import sys
from pathlib import Path

def setup():
    # Export the PYTHONPATH
    here = sys.path[0]
    pythonpath = os.environ.get('PYTHONPATH', None)
    if not pythonpath:
        pythonpath = here
    else:
        pythonpath = pythonpath.split(':')
        pythonpath.append(here)
        pythonpath = ":".join(pythonpath)    
    os.environ['PYTHONPATH'] = pythonpath

    # Export the AMP_ROOT and AMP_DATA_ROOT
    os.environ['AMP_ROOT'] = str(Path(sys.path[0], "..").resolve().absolute())
    os.environ['AMP_DATA_ROOT'] = str(Path(sys.path[0], '../data').resolve().absolute())

    # Put the amp_python container into the path 
    if 'amp_python' not in os.environ['PATH']:
        os.environ['PATH'] = str(Path(sys.path[0], "../amp_python").absolute()) + ":" + os.environ['PATH']
