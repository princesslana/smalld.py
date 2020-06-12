import logging

logger = logging.getLogger("smalld")


def log_exception(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            logger.exception("Exception thrown in SmallD.")
            raise

    return wrapper
