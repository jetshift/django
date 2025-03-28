import os
import sys
import django
from pathlib import Path


def setup_django():
    BASE_DIR = Path(__file__).resolve()
    while not (BASE_DIR / "manage.py").exists() and BASE_DIR != BASE_DIR.parent:
        BASE_DIR = BASE_DIR.parent
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jetshift.settings")
    django.setup()
