"""
Settings for the Real World API.

The values are the ones the project has always used.  Where the container
already supplied them through the environment they are read from there so the
compose file keeps working unchanged.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'insecure-2jr-1j1%i(%pqej_8_ujp9l2n1vl%^i9y390o^n&nj_(z8!+ke'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'NAME': os.environ.get('POSTGRES_DB', 'postgres'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', '0000'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}


def database_url(name=None):
    """DSN for the configured database, or for ``name`` when one is given."""
    cfg = DATABASES['default']
    return 'postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}'.format(
        user=cfg['USER'],
        password=cfg['PASSWORD'],
        host=cfg['HOST'],
        port=cfg['PORT'],
        name=name or cfg['NAME'],
    )


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

# The previous stack mounted a catch-all file server on MEDIA_URL whenever
# DEBUG was on.  MEDIA_URL and MEDIA_ROOT were never defined, which made that
# mount an empty prefix rooted at the working directory, so every otherwise
# unmatched path is answered out of the project directory.  That is part of
# the observable contract - including the exposure it creates - so it is kept.
MEDIA_URL = ''

MEDIA_ROOT = BASE_DIR

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Token',),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'USER_ID_CLAIM': 'user_id',
}
