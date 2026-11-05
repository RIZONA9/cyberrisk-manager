import sqlite3
from contextlib import closing
from pathlib import Path

import click
from flask.cli import with_appcontext

from extensions import db


@click.command("backup-db")
@click.argument("destination", type=click.Path(path_type=Path))
@with_appcontext
def backup_database(destination):
    """Write a consistent copy of the SQLite database to a new file."""
    database = db.engine.url.database
    if not database or database == ":memory:":
        raise click.ClickException("Backups require a file-backed database.")
    try:
        with destination.open("xb"):
            pass
    except OSError as error:
        raise click.ClickException(str(error)) from error
    try:
        with closing(sqlite3.connect(Path(database).as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                if target.execute("PRAGMA quick_check").fetchone() != ("ok",):
                    raise sqlite3.DatabaseError("Backup integrity check failed.")
    except (OSError, sqlite3.Error) as error:
        destination.unlink(missing_ok=True)
        raise click.ClickException(str(error)) from error
    click.echo(f"Backup saved to {destination}.")
