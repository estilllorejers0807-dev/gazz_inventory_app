
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Database connection settings
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "gazz_pos_inventory")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3307"))

    MYSQL_CURSORCLASS = "DictCursor"

    # TLS settings
    MYSQL_SSL = os.getenv("MYSQL_SSL", "false").lower() in (
        "1", "true", "yes"
    )

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    MYSQL_SSL_CA = os.getenv(
        "MYSQL_SSL_CA",
        os.path.join(BASE_DIR, "database", "isrgrootx1.pem")
    )


    # Optional aliases
    DB_HOST = MYSQL_HOST
    DB_USER = MYSQL_USER
    DB_PASSWORD = MYSQL_PASSWORD
    DB_NAME = MYSQL_DB
    DB_PORT = MYSQL_PORT
