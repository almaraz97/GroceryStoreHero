import os


class Config:
    SECRET_KEY = '5c8485000a8940797e4ee263bcfa3de6'  # os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'  # os.environ.get('SQLALCHEMY_DATABASE_URI')

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
