import logging
from time import sleep

class LWLW:
    OK = 0
    ERROR = 1
    WAIT = 255

    def run(self, pre_cleanup=False, post_cleanup=True, lwlw=True, pause=10):
        "Run a LWLW MGM.  If serial is specified, loop to completion"
        if not lwlw:
            logging.debug("Using synchronous protocol")
            if self.exists() and pre_cleanup:
                self.cleanup()
            rc = self.submit()
            logging.debug(f"Job submission return rc={rc}")
            while rc == LWLW.WAIT:
                rc = self.check()
                logging.debug(f"Check job returned rc={rc}")
                if rc == LWLW.WAIT:
                    sleep(pause)
            if post_cleanup:
                self.cleanup()

        else:
            logging.debug("Using LWLW protocol")
            if not self.exists():
                if pre_cleanup:
                    self.cleanup()
                rc = self.submit()
            else:
                rc = self.check()
            if rc == LWLW.OK and post_cleanup:
                self.cleanup()
        
        return rc

    def exists(self, *args, **kwargs):
        "Get the identifier for this job if it exists, otherwise None"
        raise NotImplementedError("The exists method must be supplied by the subclass")


    def submit(self, *args, **kwargs):
        """Submit the job for processing.  
           Returns LWLW Status values"""
        raise NotImplementedError("The submit method must be supplied by the subclass")


    def check(self, *args, **kwargs):
        """Check if the job has completed.
        Returns LWLW Status values"""
        raise NotImplementedError("The check method must be supplied by the subclass")
    
    def cleanup(self, *args, **kwargs):
        """Cleanup a job's resources"""
        raise NotImplementedError("The cleanup method must be supplied by the subclass")    
    