
class Config:
    # set env variable here
    SECRET_KEY = '5c8485000a8940797e4ee263bcfa3de6'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    #set env variable here
    MAIL_USERNAME = 'alejandro.almaraz15@gmail.com'  # os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = 'ljtxilvndxtrrznw' #'Almaraz97'  # os.environ.get('EMAIL_PASS')
