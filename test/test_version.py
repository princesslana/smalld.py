from smalld import __version__
from datetime import datetime

# tests that the version matches the date
def test_version():
    today = datetime.now().strftime("%Y%m%d")
    assert __version__.split('d')[-1] == today