from datetime import datetime
from GroceryHero import db, login_manager
from flask_login import UserMixin
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# from flask import current_app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """
    Rec:{str(list()): score} taste:{str(list()): similarity} weight:{ing:val} rec_ids:{recipe.title: recipe.id}

    Formats:
    Grocery list: [{Aisle: [Ingredients],...}, Overlapping_ings]
    Pantry: {Shelf: {Ingredient: [quantity, unit],...},...}
    History: Current: [{title:[ingredients]},...];  Future: {datetime:[{title:[ingredients]},...]}
    Ingredients: {Ingredient: [quantity, unit, price]}
    Subscription: {datetime:level(hero, super-saver, eco-warrior)}
    Messages = {}
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=False, nullable=False)
    # nickname = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    # password = db.Column(db.String(60), nullable=False)  # todo Delete this for auth0 handling
    recipes = db.relationship('Recipes', backref='author', lazy=True)
    aisles = db.relationship('Aisles', backref='author', lazy=True)
    harmony_preferences = db.Column(db.JSON, nullable=True,  # todo make these columns
                                    default={'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0,
                                             'recommended': {}, 'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {},
                                             'sticky_weights': {}, 'recipe_ids': {}, 'history': 0,
                                             'ingredient_excludes': [], 'algorithm': 'Balanced'})
    pro = db.Column(db.Boolean, nullable=False, default=False)  # Harmony Tool
    grocery_list = db.Column(db.JSON, nullable=False, default=[])  # todo False
    # overlap = db.Column(db.Integer, nullable=False, default=0)  # todo
    extras = db.Column(db.JSON, nullable=False, default=[])  # todo False
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.Column(db.JSON, nullable=False, default={})
    history = db.Column(db.JSON, nullable=False, default={})
    pantry = db.Column(db.JSON, nullable=False, default={})  # todo False
    # user_rec = db.relationship('User_Rec', backref='borrower', lazy=True)
    # follows = db.relationship('Followers', backref='follower', lazy=True)  # People they follow
    # user_pub_rec = db.relationship('User_PubRec', backref='borrower', lazy=True)  # todo be able to backref these
    actions = db.relationship('Actions', backref='author', lazy=True)
    pro2 = db.Column(db.Boolean, nullable=False, default=False)  # Friends features
    pro3 = db.Column(db.Boolean, nullable=False, default=False)  # Extra recipes
    pro4 = db.Column(db.Boolean, nullable=False, default=False)  # Extra for future use
    public = db.Column(db.Boolean, nullable=False, default=False)  # Whether they are discoverable to others
    feed_see = db.Column(db.JSON, nullable=False, default=[])  # Updates, Adds, Deletes, Clears
    feed_show = db.Column(db.JSON, nullable=False, default=[])  # Updates, Adds, Deletes, Clears
    grocery_bills = db.Column(db.JSON, nullable=False, default={})  # Track bill amount  ({datetime:float})
    ingredients = db.Column(db.JSON, nullable=False, default={})
    subscription = db.Column(db.JSON, nullable=False, default={})
    reports = db.Column(db.JSON, nullable=False, default={'Reports': [], 'Reported': []})
    timezone = db.Column(db.String(60), nullable=True)

    # def get_reset_token(self, expires_sec=1800):
    #     s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
    #     return s.dumps({'user_id': self.id}).decode('utf-8')
    #
    # @staticmethod
    # def verify_reset_token(token):
    #     s = Serializer(current_app.config['SECRET_KEY'])
    #     try:
    #         user_id = s.loads(token)['user_id']
    #     except:
    #         return None
    #     return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Recipes(db.Model):  # Recipes are first class citizens!
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.JSON, nullable=False, default={})  # Format: {ingredient: [value, unit]}
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(512), nullable=True)
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    recipe_type = db.Column(db.String(16), nullable=True)
    recipe_genre = db.Column(db.String(32), nullable=True) # Asian, Hispanic, Southern
    picture = db.Column(db.String(20), nullable=True)
    public = db.Column(db.Boolean, nullable=False, default=False)  # Public to friends
    servings = db.Column(db.Integer, nullable=True, default=0)
    times_eaten = db.Column(db.Integer, nullable=False, default=0)
    originator = db.Column(db.Integer, nullable=True)  # Original creator of the recipe, in spite of downloads
    price = db.Column(db.JSON, nullable=False, default={})  # Price per ingredient to total price
    options = db.Column(db.JSON, nullable=False, default={})

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


class Actions(db.Model):  # Where friend feed stuff will be held
    id = db.Column(db.Integer, primary_key=True)  # todo works here but not pub_rec
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type_ = db.Column(db.String(20), nullable=False)  # Update, Add, Delete, Clear, Borrow, Download, Follow
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.String(250), nullable=True)  # User can type message
    recipe_ids = db.Column(db.JSON, nullable=False, default=[])
    titles = db.Column(db.JSON, nullable=False, default=[])  # Save recipe title in case recipe is deleted
    harmony_score = db.Column(db.Float, nullable=True)  # For clears

    def __repr__(self):
        return f"Actions(User {self.user_id} {self.type_}ed {self.recipe_ids} on {self.date_created})"


class Followers(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # User
    follow_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # Person user follows
    user = db.relationship('User', foreign_keys=[user_id])
    follow = db.relationship('User', foreign_keys=[follow_id])
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        codes = {0: 'Requested', 1: 'Followed', 2: 'Unfollowed', 3: 'Blocked'}
        status = codes[self.status] if self.status in codes else 'Error'
        time = self.date_created.strftime('%Y-%m-%d')
        return f"Followers({self.user_id} {status} {self.follow_id} on {time})"


class Pub_Rec(db.Model):
    p_id = db.Column(db.Integer, primary_key=True)  # todo why is this not regular id?
    origin_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ogusername = db.Column(db.String(64), nullable=False)  # Username at time of creation
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    title = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.JSON, nullable=False)  # Format: {ingredient: [value, unit]}
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(200), nullable=True)  # 16?
    recipe_type = db.Column(db.String(16), nullable=True)
    recipe_genre = db.Column(db.String(32), nullable=True)  # Asian, Hispanic, Southern
    picture = db.Column(db.String(20), nullable=True)
    servings = db.Column(db.Integer, nullable=True, default=0)
    credit = db.Column(db.Boolean, nullable=False, default=False)
    price = db.Column(db.JSON, nullable=False, default={})  # Price per ingredient to total price
    options = db.Column(db.JSON, nullable=False, default={})

    def __repr__(self):
        return f"Pub_Rec('{self.title}', '{list(self.quantity.keys())}')"

    def __eq__(self, other):
        if isinstance(other, Recipes):
            return self.title == other.title and self.quantity.keys() == other.quantity.keys()
        return False


class User_Rec(db.Model):  # For borrowed recipes
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), primary_key=True, nullable=False)
    borrowed = db.Column(db.Boolean, nullable=False, default=False)
    borrowed_dates = db.Column(db.JSON, nullable=False, default={})  # {'Borrowed':[datetime], 'Unborrowed':[datetime]}
    downloaded = db.Column(db.Boolean, nullable=False, default=False)
    downloaded_dates = db.Column(db.JSON, nullable=False, default=[])
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    times_eaten = db.Column(db.Integer, nullable=True, default=0)
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"User_Rec(user_id: {self.user_id}, recipe_id: {self.recipe_id})"


class User_PubRec(db.Model):  # For borrowed recipes
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('pub__rec.p_id'), primary_key=True, nullable=False)
    borrowed = db.Column(db.Boolean, nullable=True, default=False)
    borrowed_dates = db.Column(db.JSON, nullable=True, default={})  # {'Borrowed':[datetime], 'Unborrowed':[datetime]}
    downloaded = db.Column(db.Boolean, nullable=True)
    downloaded_dates = db.Column(db.JSON, nullable=True, default=[])
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    times_eaten = db.Column(db.Integer, nullable=False, default=0)
    hidden = db.Column(db.Boolean, nullable=False, default=False)


class User_Act(db.Model):  # For comments and likes on other's actions
    act_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    comment = db.Column(db.String(200), nullable=True)
    liked = db.Column(db.Boolean, nullable=False, default=False)


# class User_User(db.Model):  # Messages, follow requests, etc between others
#     act_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
#     comment = db.Column(db.String(200), nullable=True)
#     liked = db.Column(db.Boolean, nullable=False, default=False)

