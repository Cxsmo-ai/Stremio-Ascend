import sys
import os
import logging
from datetime import datetime

def setup_logging():
    # DEBUG MODE: ENABLE LOGGING TO FILE
    log_file = "stremio_debug.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Also output to stdout (though console hidden)
        ]
    )
    
    # Silence noisy libs
    logging.getLogger("adb_shell").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # DO NOT redirect stderr/stdout to devnull for debug build!
    # We want to capture errors.
    # sys.stderr = open(log_file, 'a')
    # sys.stdout = open(log_file, 'a') # optional, basicConfig handles it

# Initialize logging immediately
setup_logging()
logger = logging.getLogger("StremioRPC")

class LoggerWriter:
    # Deprecated/Unused
    def __init__(self, writer): pass
    def write(self, buf): pass
    def flush(self): pass
