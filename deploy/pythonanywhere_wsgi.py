"""Copy this file into the PythonAnywhere Web tab's WSGI configuration."""
from os import environ
from pathlib import Path
import sys


home = Path.home()
project = home / "cyberrisk-manager"
configuration = home / ".config" / "cyberrisk"
sys.path.insert(0, str(project))
environ["CYBERRISK_SECRET_KEY"] = (configuration / "secret_key").read_text(encoding="utf-8").strip()
environ["CYBERRISK_HOSTNAME"] = (configuration / "hostname").read_text(encoding="utf-8").strip()

from wsgi import application  # noqa: E402
