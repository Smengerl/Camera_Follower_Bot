import logging
import sys


class CustomFormatter(logging.Formatter):
    LEVEL_PREFIX = {
        logging.DEBUG: 'D:',
        logging.INFO: 'I:',
        logging.WARNING: 'W:',
        logging.ERROR: 'E:',
        logging.CRITICAL: 'C:',
    }

    def format(self, record):
        prefix = self.LEVEL_PREFIX.get(record.levelno, '?')
        message = super().format(record)
        return f"{prefix} {message}"


def get_remote_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomFormatter('%(message)s'))
    logger.handlers = [handler]
    return logger