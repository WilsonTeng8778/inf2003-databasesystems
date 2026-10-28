"""Local database configuration; secrets are never included in command output."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", interpolate=False)


def postgres(database=None, **options):
    settings = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": database or os.getenv("POSTGRES_DB", "vehicle_safety"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "connect_timeout": 5,
    }
    settings.update(options)
    return psycopg.connect(**settings)


class AppDatabaseNotConfigured(RuntimeError):
    """The web reader's credentials have not been prepared locally."""


def app_postgres():
    user = os.getenv("APP_POSTGRES_USER", "")
    password = os.getenv("APP_POSTGRES_PASSWORD", "")
    if not user or not password:
        raise AppDatabaseNotConfigured("Run scripts/setup_readonly_user.py before starting the API")
    return postgres(user=user, password=password,
                    options="-c default_transaction_read_only=on -c statement_timeout=5000")


def auth_postgres():
    user, password = os.getenv("AUTH_POSTGRES_USER", ""), os.getenv("AUTH_POSTGRES_PASSWORD", "")
    if not user or not password:
        raise AppDatabaseNotConfigured("Run scripts/setup_auth.py before using authentication")
    return postgres(user=user, password=password,
                    options="-c default_transaction_read_only=off -c statement_timeout=5000")


def workflow_postgres():
    user, password = os.getenv("WORKFLOW_POSTGRES_USER", ""), os.getenv("WORKFLOW_POSTGRES_PASSWORD", "")
    if not user or not password:
        raise AppDatabaseNotConfigured("Run scripts/setup_workflow.py before using saved vehicles")
    return postgres(user=user, password=password,
                    options="-c default_transaction_read_only=off -c statement_timeout=5000")


def mongo_client():
    return MongoClient(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/"),
                       serverSelectionTimeoutMS=5000, tz_aware=True)


def mongo_database(client):
    return client[os.getenv("MONGODB_DB", "vehicle_safety")]

