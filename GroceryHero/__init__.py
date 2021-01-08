from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from GroceryHero.config import Config, config
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)  # Only takes config vars that overwrite app vars
    oauth = OAuth(app)
    client_secret = config.get('client_secret')
    auth0_urls = config.get('auth0_urls')
    app.client_id = config.get('client_id')
    auth0 = oauth.register(
        'auth0',
        client_id=app.client_id,
        client_secret=client_secret,
        api_base_url='https://dev-7z79kd24.us.auth0.com',
        access_token_url='https://dev-7z79kd24.us.auth0.com/oauth/token',
        authorize_url='https://dev-7z79kd24.us.auth0.com/authorize',
        client_kwargs={
            'scope': 'openid profile email',
        },
    )
    app.auth0 = auth0
    app.auth0_urls = auth0_urls

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db=db, render_as_batch=True)

    from GroceryHero.Users.routes import users
    from GroceryHero.Recipes.routes import recipes
    from GroceryHero.Main.routes import main
    from GroceryHero.Aisles.routes import aisles
    from GroceryHero.Pantry.routes import pantry
    from GroceryHero.errors.handlers import errors

    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(recipes)
    app.register_blueprint(aisles)
    app.register_blueprint(pantry)
    app.register_blueprint(errors)

    return app
