# An implementation of logging which will standardize the format and whatnot.
# * logs go to stderr 
# * if a 'logs' directory exists next to the executable, messages will also be appended to mgms.log
# * the mgms.log will be rotated automatically
import logging    
import logging.handlers
from pathlib import Path
import fcntl
import os

class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    "Multi-process-safe locking file handler"
    def __init__(self, *args, **kwargs):
        logging.handlers.TimedRotatingFileHandler.__init__(self, *args, **kwargs)
    
    def emit(self, record):        
        x = self.stream # copy the stream in case we rolled
        fcntl.lockf(x, fcntl.LOCK_EX)
        super().emit(record)
        if not x.closed:
            fcntl.lockf(x, fcntl.LOCK_UN)


def setup_logging(basename: str, debug: bool):
    "Setup the logging subsystem.  If basename is None no persistent log will be created"
    logging_level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d:%(process)d)  %(message)s")

    logger = logging.getLogger()
    logger.setLevel(logging_level)

    # set up the console handler
    console = logging.StreamHandler()
    console.setLevel(logging_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # if we have access the the AMP_DATA_ROOT environment variable
    # and the logs directory exists, then we can set up the
    # file handler.
    if basename is not None:
        if 'AMP_DATA_ROOT' in os.environ:
            try:
                log_path = Path(os.environ['AMP_DATA_ROOT'], "logs")
                if log_path.exists() and log_path.is_dir():                
                    file = TimedRotatingFileHandler(log_path / f"{basename}.log", when='midnight', encoding='utf-8')
                    file.setLevel(logging_level)
                    file.setFormatter(formatter)
                    logger.addHandler(file)
                else:
                    logging.info("Skipping persisent logging since the logs directory doesn't exist in AMP_DATA_ROOT")
            except Exception as e:
                raise OSError(f"Cannog set up logging because: {e}")
        else:
            logging.info("Skipping persistent logging since AMP_DATA_ROOT isn't set")





