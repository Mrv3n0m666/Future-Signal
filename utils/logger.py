
import logging, os
def get_logger(name=__name__):
    level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, level))
    return logging.getLogger(name)
