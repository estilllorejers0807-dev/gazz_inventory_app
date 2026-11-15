
import pymysql
from flask import current_app, g
from config import Config


class PyMySQLConnection:
    """
    Flask-compatible PyMySQL connection manager.

    Keeps the existing mysql.connection interface so application
    routes do not need to be rewritten.
    """

    _connection_key = "_gazz_pymysql_connection"

    def init_app(self, app):
        app.teardown_appcontext(self._teardown)

    def _connect(self):
        options = {
            "host": current_app.config["MYSQL_HOST"],
            "user": current_app.config["MYSQL_USER"],
            "password": current_app.config["MYSQL_PASSWORD"],
            "database": current_app.config["MYSQL_DB"],
            "port": current_app.config["MYSQL_PORT"],
            "cursorclass": pymysql.cursors.DictCursor,
            "charset": "utf8mb4",
            "connect_timeout": 15,
            "autocommit": False,
        }

        if current_app.config.get("MYSQL_SSL", False):
            options.update({
                "ssl_ca": current_app.config["MYSQL_SSL_CA"],
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            })

        return pymysql.connect(**options)

    @property
    def connection(self):
        if self._connection_key not in g:
            setattr(g, self._connection_key, self._connect())

        return getattr(g, self._connection_key)

    def _teardown(self, exception=None):
        connection = g.pop(self._connection_key, None)

        if connection is not None:
            connection.close()


mysql = PyMySQLConnection()


def init_db(app):
    """
    Initialize the PyMySQL connection manager with Flask.
    """

    app.config["MYSQL_HOST"] = Config.MYSQL_HOST
    app.config["MYSQL_USER"] = Config.MYSQL_USER
    app.config["MYSQL_PASSWORD"] = Config.MYSQL_PASSWORD
    app.config["MYSQL_DB"] = Config.MYSQL_DB
    app.config["MYSQL_PORT"] = Config.MYSQL_PORT
    app.config["MYSQL_SSL"] = Config.MYSQL_SSL
    app.config["MYSQL_SSL_CA"] = Config.MYSQL_SSL_CA

    mysql.init_app(app)

    return mysql


def get_db_connection():
    """
    Create a direct PyMySQL connection.
    """

    options = {
        "host": Config.MYSQL_HOST,
        "user": Config.MYSQL_USER,
        "password": Config.MYSQL_PASSWORD,
        "database": Config.MYSQL_DB,
        "port": Config.MYSQL_PORT,
        "cursorclass": pymysql.cursors.DictCursor,
        "charset": "utf8mb4",
        "connect_timeout": 15,
        "autocommit": False,
    }

    if Config.MYSQL_SSL:
        options.update({
            "ssl_ca": Config.MYSQL_SSL_CA,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        })

    return pymysql.connect(**options)
