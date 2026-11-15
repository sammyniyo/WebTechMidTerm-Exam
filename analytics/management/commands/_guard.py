from django.core.management.base import CommandError
from django.db import connection


def require_local_db(allow_remote):
    """Demo commands write sample rows; keep them off the shared MySQL server."""
    if connection.vendor != "sqlite" and not allow_remote:
        raise CommandError(
            f"This command writes demo data and the database is {connection.vendor}. "
            "Run with DB_ENGINE=sqlite, or pass --allow-remote if you really mean it."
        )
