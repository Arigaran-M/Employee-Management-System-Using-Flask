from datetime import timedelta

class Config:

    PERMANENT_SESSION_LIFETIME = timedelta(days = 1)
    SECRET_KEY = "123456789"
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "Ari@2003"
    MYSQL_DB = "company"
    MYSQL_CURSORCLASS = "DictCursor"