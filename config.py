import os
from secrets import token_hex


class Config:
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOW_DEMO_DATA = False
    MAX_CONTENT_LENGTH = 256 * 1024


class DevelopmentConfig(Config):
    ALLOW_DEMO_DATA = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///cyberrisk.db"

    @staticmethod
    def secret_key():
        return os.environ.get("CYBERRISK_SECRET_KEY") or token_hex(32)


class TestingConfig(Config):
    ALLOW_DEMO_DATA = True
    TESTING = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"

    @staticmethod
    def secret_key():
        return token_hex(32)


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///cyberrisk-production.db"

    @staticmethod
    def secret_key():
        key = os.environ.get("CYBERRISK_SECRET_KEY", "")
        if len(key) < 32:
            raise RuntimeError("Set CYBERRISK_SECRET_KEY to a private value of at least 32 characters.")
        return key


def configured_profile():
    profiles = {"development": DevelopmentConfig, "production": ProductionConfig}
    environment = os.environ.get("CYBERRISK_ENV", "development")
    if environment not in profiles:
        raise RuntimeError("CYBERRISK_ENV must be development or production.")
    return profiles[environment]
