from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData, event


db = SQLAlchemy(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
)
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def enable_sqlite_foreign_keys(connection, _connection_record):
    # SQLite requires foreign-key enforcement on each connection.
    connection.execute("PRAGMA foreign_keys = ON").close()


def init_database(app):
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            event.listen(db.engine, "connect", enable_sqlite_foreign_keys)
    migrate.init_app(app, db)
