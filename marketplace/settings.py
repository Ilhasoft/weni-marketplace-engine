"""
Django settings for marketplace project.

Generated by "django-admin startproject" using Django 3.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
from pathlib import Path
from datetime import timedelta
import urllib

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from corsheaders.defaults import default_headers


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent


# environ settings
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    environ.Env.read_env(env_file=ENV_PATH)

env = environ.Env()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = env.bool("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "mozilla_django_oidc",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # marketplace apps
    "marketplace.accounts",
    "marketplace.core",
    "marketplace.applications",
    "marketplace.interactions",
    "marketplace.grpc",
    # installed apps
    "rest_framework",
    "storages",
    "corsheaders",
    "django_grpc_framework",
    "drf_yasg",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "marketplace.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "marketplace.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = dict(default=env.db(var="DATABASE_URL"))


# Authentication

AUTH_USER_MODEL = "accounts.User"

ADMIN_USER_EMAIL = env("ADMIN_USER_EMAIL", default="admin@weni.ai")


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="en-us")

TIME_ZONE = env.str("TIME_ZONE", default="America/Maceio")

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# AWS Configurations

USE_S3 = env.bool("USE_S3", default=False)

MEDIA_ROOT = env.str("MEDIA_ROOT", default="media/")

if USE_S3:
    """
    Upload files to S3 bucket
    """

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")

    AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")

    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

else:
    MEDIA_URL = "/media/"


STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")


# Mozilla OIDC Configurations

USE_OIDC = env.bool("USE_OIDC")

if USE_OIDC:
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append("mozilla_django_oidc.contrib.drf.OIDCAuthentication")

    OIDC_RP_CLIENT_ID = env.str("OIDC_RP_CLIENT_ID")
    OIDC_RP_CLIENT_SECRET = env.str("OIDC_RP_CLIENT_SECRET")
    OIDC_OP_AUTHORIZATION_ENDPOINT = env.str("OIDC_OP_AUTHORIZATION_ENDPOINT")
    OIDC_OP_TOKEN_ENDPOINT = env.str("OIDC_OP_TOKEN_ENDPOINT")
    OIDC_OP_USER_ENDPOINT = env.str("OIDC_OP_USER_ENDPOINT")
    OIDC_OP_JWKS_ENDPOINT = env.str("OIDC_OP_JWKS_ENDPOINT")
    OIDC_RP_SIGN_ALGO = env.str("OIDC_RP_SIGN_ALGO", default="RS256")
    OIDC_DRF_AUTH_BACKEND = "marketplace.accounts.backends.WeniOIDCAuthenticationBackend"
    OIDC_RP_SCOPES = env.str("OIDC_RP_SCOPES", default="openid email")


# django-cors-headers Configurations

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOW_ALL_ORIGINS = env.str("CORS_ALLOW_ALL_ORIGINS", default=DEBUG)
CORS_ALLOW_HEADERS = list(default_headers) + ["project-uuid"]


# gRPC Connect Client

CONNECT_GRPC_SERVER_URL = env.str("CONNECT_GRPC_SERVER_URL")
CONNECT_CERTIFICATE_GRPC_CRT = env.str("CONNECT_CERTIFICATE_GRPC_CRT", None)

SOCKET_BASE_URL = env.str("SOCKET_BASE_URL", "")
FLOWS_HOST_URL = env.str("FLOWS_HOST_URL", "")


# gRPC Router Client

ROUTER_GRPC_SERVER_URL = env.str("ROUTER_GRPC_SERVER_URL")
ROUTER_CERTIFICATE_GRPC_CRT = env.str("ROUTER_CERTIFICATE_GRPC_CRT", None)
ROUTER_BASE_URL = env.str("ROUTER_BASE_URL")


# Redis

REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379")


# Celery

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE


# Cache

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}


# Extra configurations

APPTYPE_WENI_WEB_CHAT_PATH = "channels.weni_web_chat.type.WeniWebChatType"
APPTYPE_TELEGRAM_PATH = "channels.telegram.type.TelegramType"
APPTYPE_WHATSAPP_DEMO_PATH = "channels.whatsapp_demo.type.WhatsAppDemoType"
APPTYPE_WHATSAPP_PATH = "channels.whatsapp.type.WhatsAppType"
APPTYPE_WHATSAPP_CLOUD_PATH = "channels.whatsapp_cloud.type.WhatsAppCloudType"

APPTYPES_CLASSES = [
    APPTYPE_WENI_WEB_CHAT_PATH,
    APPTYPE_TELEGRAM_PATH,
    APPTYPE_WHATSAPP_DEMO_PATH,
    APPTYPE_WHATSAPP_PATH,
    APPTYPE_WHATSAPP_CLOUD_PATH,
]

# These conditions avoid dependence between apptypes,
# if you want to run the application without using any apptype,
# just comment it in APPTYPES_CLASSES

WHATSAPP_SYSTEM_USER_ACCESS_TOKEN = env.str("WHATSAPP_SYSTEM_USER_ACCESS_TOKEN", default="")
WHATSAPP_VERSION = env.str("WHATSAPP_VERSION", default="v13.0")
WHATSAPP_API_URL = urllib.parse.urljoin(
    env.str("WHATSAPP_API_URL", default="https://graph.facebook.com/"), WHATSAPP_VERSION
)

if APPTYPE_WHATSAPP_PATH in APPTYPES_CLASSES:
    WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS = (
        env.int("WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS", default=10) * 60 * 60
    )
    WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS = (
        env.int("WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS", default=10) * 60 * 60
    )


if APPTYPE_WHATSAPP_CLOUD_PATH in APPTYPES_CLASSES:
    WHATSAPP_CLOUD_SYSTEM_USER_ID = env.str("WHATSAPP_CLOUD_SYSTEM_USER_ID")
    WHATSAPP_CLOUD_EXTENDED_CREDIT_ID = env.str("WHATSAPP_CLOUD_EXTENDED_CREDIT_ID")

# Sentry configuration

USE_SENTRY = env.bool("USE_SENTRY", default=False)

if USE_SENTRY:
    sentry_sdk.init(
        dsn=env.str("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
    )


# gRPC Framework configurations

GRPC_FRAMEWORK = {
    "ROOT_HANDLERS_HOOK": "marketplace.grpc.urls.grpc_handlers",
}

USE_GRPC = env.bool("USE_GRPC", default=False)


# Celery

CELERY_BEAT_SCHEDULE = {
    "sync-whatsapp-apps": {"task": "sync_whatsapp_apps", "schedule": timedelta(hours=2)},
    "sync-whatsapp-wabas": {"task": "sync_whatsapp_wabas", "schedule": timedelta(hours=5)},
    "sync-whatsapp-phone-numbers": {"task": "sync_whatsapp_phone_numbers", "schedule": timedelta(hours=5)},
}
