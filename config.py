from datetime import timedelta

class Config:

    PERMANENT_SESSION_LIFETIME = timedelta(days = 1)
    SECRET_KEY = "Enter the Secret Key"
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "Enter the MySQL Password"
    MYSQL_DB = "company"
    MYSQL_CURSORCLASS = "DictCursor"