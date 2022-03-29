from datetime import datetime
from GroceryHero import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Followers(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # Following user (actively following)
    follow_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # Followed user (passively followed)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', foreign_keys=[user_id])  # Get User that is the follower
    follow = db.relationship('User', foreign_keys=[follow_id])  # Get User that is being followed
    codes = {0: 'Requested', 1: 'Followed', 2: 'Unfollowed', 3: 'Blocked'}

    def __repr__(self):
        status = self.codes[self.status] if self.status in self.codes else 'Error'
        time = self.date_created.strftime('%Y-%m-%d')
        return f"Followers({self.user_id} {status} {self.follow_id} on {time})"

    def getStatus(self):
        return self.codes[self.status]


class User(db.Model, UserMixin):
    """
    Rec:{str(list()): score} taste:{str(list()): similarity} weight:{ing:val} rec_ids:{recipe.title: recipe.id}

    Formats:
    Grocery list: [{Aisle: {Ingredient: [quantity, unit],...},...}, Overlapping_ings]  # Must be stored to track strikes
    Pantry: {Shelf: {Ingredient: [quantity, unit],...},...}
    History: Current: [{title:[ingredients]},...];  Future: {datetime:[{title:[ingredients]},...]}
    Ingredients: {Ingredient: [quantity, unit, price]}
    Subscription: {datetime:level(hero, super-saver, eco-warrior)}
    Messages = {user_id: {date: message}}
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=False, nullable=False)
    # nickname = db.Column(db.String(20), unique=False, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    recipes = db.relationship('Recipes', backref='author', lazy=True)
    aisles = db.relationship('Aisles', backref='author', lazy=True)
    harmony_preferences = db.Column(db.JSON, nullable=True,  # todo make these columns
                                    default={'excludes': [], 'similarity': 45, 'groups': 3, 'possible': 0,
                                             'recommended': {}, 'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {},
                                             'sticky_weights': {}, 'recipe_ids': {}, 'history': 0,
                                             'ingredient_excludes': [], 'algorithm': 'Balanced'})  # TODO CREATE HARMONY TABLE FOR THIS
    pro = db.Column(db.Boolean, nullable=False, default=False)  # Harmony Tool
    grocery_list = db.Column(db.JSON, nullable=False, default=[])  # todo False, make dict instead of [gl, overlap]
    # overlap = db.Column(db.Integer, nullable=False, default=0)  # todo
    extras = db.Column(db.JSON, nullable=False, default=[])  # todo False
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    messages = db.Column(db.JSON, nullable=False, default={})
    history = db.Column(db.JSON, nullable=False, default={})
    pantry = db.Column(db.JSON, nullable=False, default={})  # todo False

    borrows = db.relationship('User_Rec', backref='borrower', lazy=True)
    # follows = db.relationship('Followers', backref='follower', lazy=True)  # People they follow
    # followed = db.relationship(
    #     'User', secondary=Followers,
    #     primaryjoin=(Followers.user_id == id),
    #     secondaryjoin=(Followers.follow_id == id),
    #     backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
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
    # last_stat_gen = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    # following = db.relationship('Followers', foreign_keys='user_id')  # , lazy=True

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

    @property
    def all_recipes(self):
        all_recipes = User_Rec.query.filter_by(recipe_id=self.id, borrowed=True)
        return all_recipes + self.recipes


class Recipes(db.Model):  # Recipes are first class citizens!
    """ quantity column  # WIP
    {section title:  # If title is <"MAIN"> then don't display it as a section
        {ingredient:
            [value, unit, descriptor(optional, chopped, dried), brand?]
            OR
            {value: float, unit: str, descriptor: str, brand: str}
        }
    }
    OR just
    {ingredient:
            [value, unit, descriptor(optional, chopped, dried), brand?]
            or
            {value: float, unit: str, descriptor: str, brand: str}
        }
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.JSON, nullable=False, default={})  # Format: {ingredient: [value, 'description', unit]}
    in_menu = db.Column(db.Boolean, nullable=False, default=False)
    eaten = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(512), nullable=True)  # 1024
    recipe_type = db.Column(db.String(16), nullable=True)  # Breakfast, Lunch, etc
    picture = db.Column(db.String(20), nullable=True)
    times_eaten = db.Column(db.Integer, nullable=False, default=0)
    recipe_genre = db.Column(db.String(32), nullable=True)  # Asian, Hispanic, Southern
    public = db.Column(db.Boolean, nullable=False, default=False)  # Public recipe
    servings = db.Column(db.Integer, nullable=False, default=1)
    originator = db.Column(db.Integer, nullable=True)  # Original recipe ID, in spite of downloads
    price = db.Column(db.JSON, nullable=False, default={})  # Price per ingredient to total price
    borrows = db.relationship('User_Rec', backref='source', lazy=True)  # Borrowed versions of the recipe

    options = db.Column(db.JSON, nullable=False, default={})  # Optional/replacement ingredient {ing: ['opt', 'rep']}
    # todo have options as reference to quantity dict or its own quantity dict for optional items?
    # sections = db.Column(db.JSON, nullable=False, default={})  # {'main': [ingredients], 'sauce':[ingredients]}, null?
    restrictions = db.Column(db.JSON, nullable=False, default=[])
    # gluten-free = db.Column(db.Boolean, nullable=False, default=False)
    # lactose-free = db.Column(db.Boolean, nullable=False, default=False)
    # lactose-free = db.Column(db.Boolean, nullable=False, default=False)
    # nut-free = db.Column(db.Boolean, nullable=False, default=False)
    # wheat-free = db.Column(db.Boolean, nullable=False, default=False)
    # shellfish-free = db.Column(db.Boolean, nullable=False, default=False)
    # egg-free = db.Column(db.Boolean, nullable=False, default=False)
    # soy-free = db.Column(db.Boolean, nullable=False, default=False)
    # low-fat = db.Column(db.Boolean, nullable=False, default=False)
    # low-carb = db.Column(db.Boolean, nullable=False, default=False)
    # low-calorie = db.Column(db.Boolean, nullable=False, default=False)
    # low-salt = db.Column(db.Boolean, nullable=False, default=False)
    # vegetarian = db.Column(db.Boolean, nullable=False, default=False)
    # vegan = db.Column(db.Boolean, nullable=False, default=False)
    # kosher = db.Column(db.Boolean, nullable=False, default=False)
    # diabetic = db.Column(db.Boolean, nullable=False, default=False)
    # difficulty = db.Column(db.Integer, nullable=True)  # 1-5 rating
    nft_id = db.Column(db.Integer, nullable=True)  # ID of the minted nft corresponding to this recipe
    prep_time = db.Column(db.JSON, nullable=False, default={})  # prep time, cook time, etc
    nutrition = db.Column(db.JSON, nullable=False, default={})  # Vitamin A: 100mcg
    glycemic_index = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(512), nullable=True)  # Where users can write about their life & recipe
    private = db.Column(db.Boolean, nullable=False, default=False)  # Only ?friends can see
    credit = db.Column(db.Boolean, nullable=False, default=False)  # If they want their name shown to non-friends

    def __repr__(self):
        return f"Recipes({self.id}: {self.title[:6]}.., ings: {len(self.quantity.keys())}, Date: {self.date_created.strftime('%Y-%m-%d')}')"

    def __eq__(self, other):
        if isinstance(other, Recipes):
            return (self.title == other.title) and (self.quantity.keys() == other.quantity.keys())
        return False

    def to_schema(self):
        """Converts recipe into https://schema.org/Recipe format"""
        schema_diets = ['Diabetic', 'GlutenFree', 'Halal', 'Hindu', 'Kosher', 'LowCalorie',
                        'LowFat', 'LowLactose', 'LowSalt', 'Vegan', 'Vegetarian']
        # diets = [self.diabetic, self.gluten-free, self.halal, self.hindu, self.kosher, self.low-calorie,
        # self.low-fat, self.lactose-free, self.low-salt, self.vegan, self.vegetarian]
        schema = {'cookTime': self.prep_time.keys().sum(),
                  'cookingMethod': '',  # frying, steaming...
                  'nutrition': self.nutrition,
                  'recipeCategory': self.recipe_type,
                  'recipeCuisine': self.recipe_genre,
                  'recipeIngredient': self.quantity.keys(),
                  'recipeInstructions': self.notes,
                  'recipeYield': self.servings,
                  'suitableForDiet': []}  # [k for k, v in zip(schema_diets, diets) if v]
        return schema

    def ingredients(self):
        """Returns recipe ingredients with optional ingredients added if they are marked as wanted"""
        ingredients = self.quantity | {k: v for k, v in self.options.items() if v}
        return ingredients


class User_Rec(db.Model):  # Borrowed recipes
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

    comments = db.Column(db.JSON, nullable=False, default={})  # {Date: str}  # If person comments on recipe_id
    diffs = db.Column(db.JSON, nullable=False, default={})  # Ingredients to switch from original recipe
    # options = db.Column(db.JSON, nullable=False, default={})  # Optional/replacement ingredient {ing: ['opt', 'rep']}
    # todo cant change more than 50% of it? Maybe someone who eat a modified one contributes eatens?

    def __repr__(self):
        return f"User_Rec(user_id: {self.user_id}, recipe_id: {self.recipe_id})"

    def ingredients(self):
        """Returns ingredients of the original recipe and the changes the borrower makes to the recipe"""
        return


class Aisles(db.Model):  # todo make shelf table?
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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type_ = db.Column(db.String(20), nullable=False)  # Update, Add, Delete, Clear, Borrow, Download, Follow
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.String(250), nullable=True)  # User can type message
    recipe_ids = db.Column(db.JSON, nullable=False, default=[])
    titles = db.Column(db.JSON, nullable=False, default=[])  # Save recipe title in case recipe is deleted
    harmony_score = db.Column(db.Float, nullable=True)  # For clears

    def __repr__(self):
        return f"Actions(User {self.user_id} {self.type_}ed {self.recipe_ids} on {self.date_created})"


class User_Act(db.Model):  # For comments and likes on other's actions
    act_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    comment = db.Column(db.String(200), nullable=True)
    liked = db.Column(db.Boolean, nullable=False, default=False)


# class User_User(db.Model):  # Messages, etc between others
#     act_id = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
#     comment = db.Column(db.String(200), nullable=True)
#     liked = db.Column(db.Boolean, nullable=False, default=False)

