"""
Django settings for police_analytics project — NPF Geo Incidents.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── GeoDjango / GIS Library Paths ────────────────────────────────────────────
# These DLLs are bundled with the GDAL Python wheel installed in the venv.
_OSGEO_DIR = BASE_DIR / '.venv' / 'Lib' / 'site-packages' / 'osgeo'

GDAL_LIBRARY_PATH = str(_OSGEO_DIR / 'gdal.dll')
GEOS_LIBRARY_PATH = str(_OSGEO_DIR / 'geos_c.dll')

# mod_spatialite.dll — look in multiple known locations
_SPATIALITE_SEARCH_PATHS = [
    str(BASE_DIR / 'lib' / 'mod_spatialite-5.1.0-win-amd64' / 'mod_spatialite.dll'),
    str(BASE_DIR / 'lib' / 'mod_spatialite.dll'),
    str(_OSGEO_DIR / 'mod_spatialite.dll'),
    r'C:\OSGeo4W\bin\mod_spatialite.dll',
]
SPATIALITE_LIBRARY_PATH = None
for _p in _SPATIALITE_SEARCH_PATHS:
    if os.path.exists(_p):
        SPATIALITE_LIBRARY_PATH = _p
        # Add the directory to PATH so dependent DLLs are found
        os.environ['PATH'] = os.path.dirname(_p) + ';' + os.environ.get('PATH', '')
        break
# ──────────────────────────────────────────────────────────────────────────────

SECRET_KEY = 'django-insecure-npf-geo-incidents-dev-key-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # GeoDjango — must come before our app
    'django.contrib.gis',
    # NPF Geo Incidents app
    'npf_geo_incidents',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'police_analytics.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'police_analytics.wsgi.application'


# ─── Database: SpatiaLite (SQLite + spatial extension) ───────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': BASE_DIR / 'db.spatialite',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
