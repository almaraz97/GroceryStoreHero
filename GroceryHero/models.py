import json
from datetime import datetime
from GroceryHero import db, login_manager
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    recipes = db.relationship('Recipes', backref='author', lazy=True)
    aisles = db.relationship('Aisles', backref='author', lazy=True)
    """Rec:{str(list()): score} taste:{str(list()): similarity} weight:{ing:val} rec_ids:{recipe.title: recipe.id}"""
    harmony_preferences = db.Column(db.JSON, nullable=True,
                                    default={'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0,
                                             'recommended': {}, 'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {},
                                             'sticky_weights': {}, 'recipe_ids': {}, 'history': 0,
                                             'ingredient_excludes': [], 'algorithm': 'Balanced'})
    pro = db.Column(db.Boolean, nullable=False, default=False)
    grocery_list = db.Column(db.JSON, nullable=True)
    extras = db.Column(db.JSON, nullable=True, default=[])
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.Column(db.JSON, nullable=False, default=[])
    history = db.Column(db.JSON, nullable=False, default=[])  # Eating history
    friend_requests = db.Column(db.JSON, nullable=False, default=[])
    friends = db.Column(db.JSON, nullable=False, default=[])
    # {Shelf: {Ingredient: [quantity, unit],...},...}
    pantry = db.Column(db.JSON, nullable=True, default={})

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Recipes(db.Model):  # Add picture of recipe in recipe page
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.JSON, nullable=True)  # Format: {ingredient: [value, unit]}
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(20), nullable=True)
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    recipe_type = db.Column(db.String(16), nullable=True)  # Asian, Hispanic, Southern
    picture = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    public = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    servings = db.Column(db.Integer, nullable=True, default=0)
    # downloads = db.Column(db.Integer, nullable=True, default=0)
    # other_eaten = db.Column(db.Integer, nullable=True, default=0)

    def __repr__(self):
        return f"Recipes('{self.title}', '{list(self.quantity.keys())}')"

    def __eq__(self, other):
        if isinstance(other, Recipes):
            return self.title == other.title and self.quantity.keys() == other.quantity.keys()
        return False


class Aisles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    store = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Aisles('{self.title}', '{self.content}')"

    def __eq__(self, other):
        if isinstance(other, Aisles):
            return self.title == other.title and self.content == other.content
        return False

# class Pantry(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(50), nullable=False)
#     date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     content = db.Column(db.Text, nullable=False)
#     {'Category1', ['measurementObj', 'measurementObj'], 'Category2', ['measurementObj', 'measurementObj']}
#     pantry = db.Column(db.JSON, nullable=False, default={})  # filled with measurement type objects
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#
#     def __repr__(self):
#         return f"Pantry('{self.title}', '{self.content}')"
#
#     def __eq__(self, other):
#         if isinstance(other, Pantry):
#             return self.title == other.title and self.content == other.content
#         return False

# toy_user = User()
# toy_user.recipes = [Recipes(title='Burgers', quantity=None, notes=None, link=None, in_menu=True),
#                     Recipes(title='Tacos', quantity=None, notes=None, link=None, in_menu=True),
#                     Recipes(title='Chicken Soup', quantity=None, notes=None, link=None, in_menu=True),
#                     Recipes(title='Turkey Panini', quantity=None, notes=None, link=None, in_menu=False),
#                     Recipes(title='Potato Salad', quantity=None, notes=None, link=None, in_menu=False)]
# toy_user.aisles = [Aisles(title='Dairy', content=None, order=3, store='Trader Pub\'s Club'),
#                    Aisles(title='Frozen', content=None, order=4, store='Trader Pub\'s Club'),
#                    Aisles(title='Snacks', content=None, order=5, store='Trader Pub\'s Club'),
#                    Aisles(title='Meat', content=None, order=2, store='Trader Pub\'s Club'),
#                    Aisles(title='Produce', content=None, order=1, store='Trader Pub\'s Club')]
# toy_user.username = "Your Name Here"
# toy_user.email = "YourEmail@email.com"
# toy_user.harmony_preferences = {'excludes': [], 'similarity': 50, 'groups': 2, 'possible': 0, 'recommended': {},
#                                 'recommend_num': 3, 'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {},
#                                 'recipe_ids': {}, 'menu_weight': 1}
# date_created=datetime.utcnow,
