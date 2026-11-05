"""Production WSGI entry point."""
from os import environ

from app import create_app
from config import ProductionConfig


application = create_app(ProductionConfig)
if hostname := environ.get("CYBERRISK_HOSTNAME"):
    application.config["TRUSTED_HOSTS"] = [hostname]
