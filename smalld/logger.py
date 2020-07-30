import contextlib
import logging

logger = logging.getLogger("smalld")


@contextlib.contextmanager
def suppress_logging(name):
    suppress = logging.getLogger(name)
    suppress.disabled = True
    yield
    suppress.disabled = False
