from datetime import datetime
from GroceryHero import db, login_manager
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app


# Only allow users to have 25 recipes as their own and 25 as borrowed from others


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """
    Rec:{str(list()): score} taste:{str(list()): similarity} weight:{ing:val} rec_ids:{recipe.title: recipe.id}
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    recipes = db.relationship('Recipes', backref='author', lazy=True)
    aisles = db.relationship('Aisles', backref='author', lazy=True)
    harmony_preferences = db.Column(db.JSON, nullable=True,
                                    default={'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0,
                                             'recommended': {}, 'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {},
                                             'sticky_weights': {}, 'recipe_ids': {}, 'history': 0,
                                             'ingredient_excludes': [], 'algorithm': 'Balanced'})
    pro = db.Column(db.Boolean, nullable=False, default=False)  # Harmony Tool
    grocery_list = db.Column(db.JSON, nullable=True)
    extras = db.Column(db.JSON, nullable=True, default=[])

    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.Column(db.JSON, nullable=False, default=[])  # {}
    history = db.Column(db.JSON, nullable=False, default=[])  # {datetime:[{title:[ingredients]},...]}
    pantry = db.Column(db.JSON, nullable=True, default={})  # #{Shelf: {Ingredient: [quantity, unit],...},...}

    # todo be able to backref here
    # user_rec = db.relationship('User_Rec', backref='borrower', lazy=True)
    # follows = db.relationship('Followers', backref='follower', lazy=True)  # People they follow
    # user_pub_rec = db.relationship('User_PubRec', backref='borrower', lazy=True)
    actions = db.relationship('Actions', backref='author', lazy=True)
    pro2 = db.Column(db.Boolean, nullable=False, default=False)  # Friends features
    pro3 = db.Column(db.Boolean, nullable=False, default=False)  # Extra recipes
    pro4 = db.Column(db.Boolean, nullable=False, default=False)  # Extra
    public = db.Column(db.Boolean, nullable=False, default=False)
    feed_see = db.Column(db.JSON, nullable=False, default=[])  # Updates, Adds, Deletes, Clears
    feed_show = db.Column(db.JSON, nullable=False, default=[])  # Updates, Adds, Deletes, Clears
    recipe_hide = db.Column(db.JSON, nullable=False, default=[])  # Hidden recipe ids
    grocery_bills = db.Column(db.JSON, nullable=False, default={})  # Track bill amount  ({datetime:float})
    ingredients = db.Column(db.JSON, nullable=False, default={})   # {Ingredient: [quantity, unit, price]}
    subscription = db.Column(db.JSON, nullable=False, default={})  # {datetime:level(hero, super-saver, eco-warrior)}

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


class Recipes(db.Model):  # todo add picture of recipe in recipe_single page
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.JSON, nullable=True)  # Format: {ingredient: [value, unit]}
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(512), nullable=True)
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    recipe_type = db.Column(db.String(16), nullable=True)
    recipe_genre = db.Column(db.String(32), nullable=True) # Asian, Hispanic, Southern
    picture = db.Column(db.String(20), nullable=True)
    public = db.Column(db.Boolean, nullable=False, default=False)  # Public to friends
    servings = db.Column(db.Integer, nullable=True, default=0)
    # # price = db.Column(db.Integer, nullable=True, default=0)  # Price per ingredient to total price
    # # optionals = db.Column(db.JSON, nullable=True, default={})

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


class Followers(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    follow_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User', foreign_keys=[user_id])
    follow = db.relationship('User', foreign_keys=[follow_id])
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        convert = {0: 'Requested', 1: 'Followed', 2: 'Unfollowed', 3: 'Blocked'}
        time = self.date_created
        return f"Followers({self.user_id} {convert[self.status]} {self.follow_id} on {time})"


class User_Rec(db.Model):  # For borrowed recipes
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), primary_key=True)
    borrowed = db.Column(db.Boolean, nullable=False, default=False)
    borrowed_dates = db.Column(db.JSON, nullable=False, default={})  # {'Borrowed':[datetime], 'Unborrowed':[datetime]}
    downloaded = db.Column(db.Boolean, nullable=False, default=False)
    downloaded_dates = db.Column(db.JSON, nullable=False, default=[])
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)


class Actions(db.Model):  # Where friends feed stuff will be held
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type_ = db.Column(db.String(20), nullable=False)  # Update, Add, Delete, Clear, Borrow, Download
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.String(250), nullable=True)
    # comments = db.Column(db.JSON, nullable=True, default={})  # {user_id: [comment, datetime]
    # likes = db.Column(db.JSON, nullable=True, default={})  # {user_id: datetime}

    def __repr__(self):
        return f"Actions('{self.type_}', '{self.content}', '{self.date_created}')"


class Pub_Rec(db.Model):  # Add picture of recipe in recipe page
    p_id = db.Column(db.Integer, primary_key=True)
    origin_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    title = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.JSON, nullable=False)  # Format: {ingredient: [value, unit]}
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(200), nullable=True)  # 16?
    recipe_type = db.Column(db.String(16), nullable=True)
    recipe_genre = db.Column(db.String(32), nullable=True) # Asian, Hispanic, Southern
    picture = db.Column(db.String(20), nullable=True)
    servings = db.Column(db.Integer, nullable=True, default=0)
    # # price = db.Column(db.Integer, nullable=True, default=0)  # Price per ingredient to total price
    # # optionals = db.Column(db.JSON, nullable=True, default={})

    def __repr__(self):
        return f"Pub_Rec('{self.title}', '{list(self.quantity.keys())}')"

    def __eq__(self, other):
        if isinstance(other, Recipes):
            return self.title == other.title and self.quantity.keys() == other.quantity.keys()
        return False


# class User_PubRec(db.Model):  # For borrowed recipes
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
#     recipe_id = db.Column(db.Integer, db.ForeignKey('pub__rec.p_id'), primary_key=True)
#     borrowed = db.Column(db.Boolean, nullable=True, default=False)
#     borrowed_dates = db.Column(db.JSON, nullable=True, default={})  # {'Borrowed':[datetime], 'Unborrowed':[datetime]}
#     downloaded = db.Column(db.Boolean, nullable=True)
#     downloaded_dates = db.Column(db.JSON, nullable=True, default=[])
#     in_menu = db.Column(db.Boolean, nullable=False, default=False)
#     eaten = db.Column(db.Boolean, nullable=False, default=False)


# Once you make a recipe public it cannot be changed. It is linked to your version
# class Pub_Recs(db.Model):  # Add picture of recipe in recipe page
#     id = db.Column(db.Integer, primary_key=True)
#     origin_id = db.Column(db.Integer, nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     title = db.Column(db.String(50), nullable=False)
#     date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     quantity = db.Column(db.JSON, nullable=True)  # Format: {ingredient: [value, unit]}
#     notes = db.Column(db.Text, nullable=True)
#     link = db.Column(db.String(20), nullable=True)
#     recipe_type = db.Column(db.String(16), nullable=True)  # Asian, Hispanic, Southern
#     picture = db.Column(db.String(20), nullable=True)
#     servings = db.Column(db.Integer, nullable=True, default=0)
#     # # Key is user ID, Value is datetime
#     # downloads = db.Column(db.JSON, nullable=True, default={})
#     # other_eaten = db.Column(db.Integer, nullable=True, default=0)
#     # # Key is user ID, value is Bool for their menu
#     # others_menu = db.Column(db.JSON, nullable=True, default={})
#
#     def __repr__(self):
#         return f"PubRecs('{self.title}', '{list(self.quantity.keys())}')"
#
#     def __eq__(self, other):
#         if isinstance(other, Recipes):
#             return self.title == other.title and self.quantity.keys() == other.quantity.keys()
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
