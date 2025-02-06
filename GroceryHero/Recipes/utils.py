from datetime import datetime, timedelta
from difflib import SequenceMatcher
import pytz
from flask import url_for, request
from flask_login import current_user
from sqlalchemy import or_, and_
from math import ceil
from GroceryHero import db
from GroceryHero.Modeling.HarmonyTool import recipe_stack
from GroceryHero.models import Recipes, Followers, User, User_Rec

class Measurements:
    Measures = ['Unit', 'Package', 'Can', 'Bottle', 'Jar', 'US Cup', 'US Tablespoon', 'US Teaspoon', 'US Fluid Ounce',
                'Ounce', 'Pound', 'Milligram', 'Gram', 'Kilogram', 'Milliliter', 'Liter']
    # 'US Pint', 'US Quart', 'US Gallon',

    Volumes = ['US Cup', 'US Fluid Ounce', 'US Tablespoon', 'US Teaspoon']  # 'US Gallon', 'US Quart', 'US Pint',
    Weights = ['Pound', 'Ounce']
    Generic = ['Unit', 'Package', 'Can', 'Bottle', 'Jar']

    Metric_Volumes = ['Liter', 'Milliliter']
    Metric_Weights = ['Kilogram', 'Gram', 'Milligram']

    Convert = {'US Gallon': 768, 'US Quart': 192, 'US Pint': 96, 'US Cup': 48.6922, 'US Fluid Ounce': 6,
               'US Tablespoon': 3, 'US Teaspoon': 1, 'Liter': 1000, 'Milliliter': 1,
               'Pound': 16, 'Ounce': 1,
               'Kilogram': 1e+6, 'Gram': 1000, 'Milligram': 1}  # To lowest [teaspoon, ounce, milligram]
    Dict_func = (lambda V=Volumes, W=Weights, G=Generic, MV=Metric_Volumes, M=Measures:  # Given str return its type
                 {x: ('Volume' if x in V else
                      ('Weight' if x in W else
                       ('Generic' if x in G else
                        ('Metric_Volumes' if x in MV else 'Metric_Weights')))) for x in M})
    Measure_dict = Dict_func()  # from unit to type

    def __init__(self, value, unit, name=None):
        if unit not in self.Measures:
            raise AssertionError("Must be in Measurement types: Volumes, Weights, Generic.")
        self.unit = unit
        self.metric_system = True if unit in self.Metric_Volumes + self.Metric_Weights else False
        self.value = value
        self.name = name
        if self.unit in self.Generic:
            self.type = 'Generic'
        else:
            if self.metric_system:  # Should I do both volumes/weight & metric or Volume_metric/Weight_metric
                self.type = 'Volume' if self.unit in self.Metric_Volumes else 'Weight'
            else:
                self.type = 'Volume' if self.unit in self.Volumes else 'Weight'

    def compatible(self, other, error=False):
        if error:
            if not isinstance(other, Measurements):
                raise AssertionError('Must be of class Measurements')
            if not self.metric_system == other.metric_system:
                raise AssertionError('Must agree in measurement system')
            if self.type != other.type:
                AssertionError('Cannot merge objects of different measure type')
            if (self.type == 'Generic') and (self.unit != other.unit):
                raise AssertionError('Must agree in Generic unit')
        else:
            if not isinstance(other, Measurements):
                return False  # raise AssertionError('Must be of class Measurements')
            if self.metric_system != other.metric_system:
                return False
            if self.type != other.type:
                return False
            if (self.type == 'Generic') and (self.unit != other.unit):  # One generic other not
                return False
            return True

    @staticmethod
    def str_compatible(str1, str2):
        if str1 in Measurements.Measure_dict:
            str1 = Measurements.Measure_dict[str1]
        else:
            raise AssertionError('Not a valid unit Measurement unit')
        if str2 in Measurements.Measure_dict:
            str2 = Measurements.Measure_dict[str2]
        else:
            raise AssertionError('Not a valid unit Measurement unit')
        return str1 == str2

    def to_str(self, system=False, type_=False):
        self.value = int(self.value) if float(self.value).is_integer() else self.value
        if (not system) and (not type_):
            return [self.name, self.value, self.unit]
        elif not system:
            return [self.name, self.value, self.unit, self.type]
        elif not type_:
            return [self.name, self.value, self.unit, self.metric_system]
        else:
            return [self.name, self.value, self.unit, self.type, self.metric_system]

    # @staticmethod
    # def convert_to_lowest_total(self, other):  # todo add this to __add__ and __sub__
    #     self.value = self.Convert[self.unit] * self.value  # convert to lowest
    #     other.value = other.Convert[other.unit] * other.value  # convert to lowest
    #     total = self.value + other.value
    #     return total

    # todo combine adding and subtracting
    def __add__(self, other, rounding=2, sub=False):  # todo this changes the unit since it is changing the self. stuff
        self.compatible(other, error=True)
        name = self.name if self.name == other.name else None
        if self.type == 'Generic':
            total = self.value + other.value
            return Measurements(name=name, value=round(total, rounding), unit=self.unit)
        value1 = self.Convert[self.unit] * self.value  # convert to lowest
        value2 = other.Convert[other.unit] * other.value  # convert to lowest
        total = value1 + value2
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric_system else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    self.unit = volume
                    return Measurements(name=name, value=round(total, 2), unit=volume)
        elif self.type == 'Weight':
            weights = self.Metric_Weights if self.metric_system else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    self.unit = weight
                    return Measurements(name=name, value=round(total, 2), unit=weight)
        return Measurements(name=name, value=round(total, 2), unit=self.unit)  # todo does this unit always work?

    def __sub__(self, other, rounding=2):
        self.compatible(other, error=True)
        name = self.name if self.name == other.name else None
        if self.type == 'Generic':
            total = self.value - other.value
            return Measurements(name=name, value=round(total, 2), unit=self.unit)
        value1 = self.Convert[self.unit] * self.value  # convert to lowest
        value2 = other.Convert[other.unit] * other.value  # convert to lowest
        total = value1 - value2
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric_system else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    self.unit = volume
                    return Measurements(name=name, value=round(total, 2), unit=volume)
        elif self.type == 'Weight':
            weights = self.Metric_Weights if self.metric_system else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    self.unit = weight
                    return Measurements(name=name, value=round(total, 2), unit=weight)
        return Measurements(name=name, value=round(total, 2), unit=self.unit)

    def __eq__(self, other):  # Check if two ingredients share name and compatible units # todo AND identical values??
        if self.compatible(other, error=False):
            return self.name == other.name  # Make this optional?
        else:
            return False

    def __repr__(self):
        unit = self.unit + 's' if self.value != 1 else self.unit
        return f'Measure({self.name}: {self.value} {unit})'


from GroceryHero.Recipes.forms import FullQuantityForm


def get_recipe_history(user_recipe_history):
    if not user_recipe_history: # Validate a logged in user
        return []
    return [[title[0] for title in Recipes.query.with_entities(Recipes.title)
                                   .filter(Recipes.id.in_(sublist)).all()]
                for sublist in user_recipe_history.values()]

def exclude_recent_recipes(recipe_history, history_exclusion_preference):
    # Preference for how many clears back should be excluded
    return [item for sublist in recipe_history[:int(history_exclusion_preference)]
                for item in sublist] 

def get_search_params(all_friends): 
    VALID_SORT_OPTIONS = {'hot', 'borrow', 'date', 'eaten', 'alpha'}
    VALID_TYPE_OPTIONS = {
        'all', 'Breakfast', 'Lunch', 'Dinner', 'Snack', 
        'Side', 'Dessert', 'Other', 'Beverage', 'Drink'
    }

    page = request.args.get('page', default=1, type=int)
    
    search = request.form.get('search')
    search = None if search in {'Recipe Options', ''} else search

    sort = request.args.get('sort', default='none')
    sort = sort if sort in VALID_SORT_OPTIONS else 'none'

    types = request.args.get('types', default='all')
    types = types if types in VALID_TYPE_OPTIONS else 'all'

    friend_id = request.args.get('friend', type=int)
    friend_choice = list(all_friends.keys()) if friend_id is None else [friend_id]

    return search, page, sort, types, friend_choice


def parse_ingredients(ingredients):
    specials = {'¼': '1/4', '½': '1/2', '¾': '3/4', '⅐': '1/7', '⅑': '1/9', '⅒': '1/10', '⅓': '1/3', '⅔': '2/3',
                '⅕': '1/5', '⅖': '2/5', '⅗': '3/6', '⅘': '4/5', '⅙': '1/6', '⅚': '5/6', '⅛': '1/8', '⅜': '3/8',
                '⅝': '5/8', '⅞': '7/8'}
    measures = Measurements.Measures
    # todo Make sure that a space or nothing is after the measurement
    extras = ['cup', 'tablespoon', 'teaspoon', 'fluid ounce', 'tsp', 'tbsp', 'oz', 'lb', 'mg', 'fl oz', 'ml', 'g']
    convert = {'Unit': 'Unit', 'Package': 'Package', 'Can': 'Can', 'Bottle': 'Bottle', 'Jar': 'Jar', 'US Cup': 'US Cup',
               'US Tablespoon': 'US Tablespoon', 'US Teaspoon': 'US Teaspoon', 'US Fluid Ounce': 'US Fluid Ounce',
               'Ounce': 'Ounce', 'Pound': 'Pound', 'Milligram': 'Milligram', 'Gram': 'Gram', 'Kilogram': 'Kilogram',
               'Milliliter': 'Milliliter', 'Liter': 'Liter',
               'cup': 'US Cup', 'tablespoon': 'US Tablespoon', 'teaspoon': 'US Teaspoon',
               'fluid ounce': 'US Fluid Ounce', 'tsp': 'US Teaspoon', 'tbsp': 'US Tablespoon', 'oz': 'Ounce',
               'lb': 'Pound', 'mg': 'Milligram', 'fl oz': 'US Fluid Ounce', 'ml': 'Milliliter', 'g': 'Gram'
               }  # 'c': 'US Cup'
    # convert = {(k if all([x not in k for x in extras]) else extras[extras.index(k)]): k for k in measures}
    measures = measures + extras
    quantity = []
    ings = []
    temp = []
    for ingredient in ingredients:  # Switch special characters to regular ones
        temp1 = ''
        for char in ingredient:
            char = specials[char] if char in specials else char
            temp1 = temp1 + char
        temp.append(temp1)
    ingredients = temp
    for i, ingredient in enumerate(ingredients):
        # print(ingredient)
        temp = ''  # New string for ingredient in ingredients list, gets chars appended as it goes through
        nums = ''  # String for holding quantity value
        cons = 0  # For remembering if last character was a number (consecutive, counts which index has the last number)
        flag = False  # For remembering if the last character was a space (ie '2 1/2', '1.5', '1 5 ounce __')
        empty = False
        for j, char in enumerate(ingredient):  # Getting the quantity and measurements
            try:
                if isinstance(float(char), float):  # Need to be able to parse fractions and decimals (keep it a char)
                    nums = nums + char
                    cons = j
            except ValueError:
                if len(nums) > 0:  # Number may have ended ended
                    if (char == '/' or char == '.') and (cons + 1) == j:  # If there is a number before the / add it
                        nums = nums + char
                    elif char == ' ':
                        nums = nums + char
                        flag = True
                    else:
                        flag = False if (cons + 1) == j else flag  # If there was a separator and last char is digit
                        if flag:
                            quantity.append([nums[:-1]])
                        else:  # Quantity string is done
                            quantity.append([nums])
                        temp = temp + ingredient[j:]  # A number is found, add the rest of the string
                        break
                elif j == len(ingredient) - 1:  # No quantity found
                    quantity.append([])
                else:
                    temp = temp + char

        if quantity[i]:  # The list is not empty
            if ('/' in quantity[i][0]) and (' ' in quantity[i][0]):  # Convert mixed fraction to fraction
                temp1 = quantity[i][0]
                quantity[i][0] = str((int(temp1[0]) * int(temp1[4])) + int(temp1[2])) + '/' + temp1[4]
            elif '.' in quantity[i][0]:
                quantity[i][0] = quantity[i][0].strip()
            elif ' ' in quantity[i][0]:  # Convert number of a certain sized quantity ('1 15 ounce can")
                numbers = quantity[i][0].split(' ')
                quantity[i][0] = int(numbers[0]) * float(numbers[1])
        else:
            quantity[i].append('1')  # Might want to flag to user that this value defaulted
        # The string of text loaded into the form for the user to see, concat each ingredient
        ings.append(' '.join([x.strip() for x in temp.split(' ') if x != ' ' and x != '']))
        found = False  # todo find '1 15 ounce can' and include only one of the units
        for measure in measures:
            # print(ings[i])
            length = len(measure)  # In case unit is the first part of the string
            if ' ' + measure.lower() + 's ' in ings[i]:  # Surrounded by space and plural
                ings[i] = ings[i].replace(' ' + measure.lower() + 's ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            elif ' ' + measure.lower() + ' ' in ings[i]:  # Surrounded by space
                ings[i] = ings[i].replace(' ' + measure.lower() + ' ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            # Search at the start of the string
            elif ings[i][:length + 2] == measure.lower() + 's ':  # First word and plural with space at end
                ings[i] = ings[i].replace(measure.lower() + 's ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            elif ings[i][:length + 1] == measure.lower() + ' ':  # First word with space at end
                ings[i] = ings[i].replace(measure.lower() + ' ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            # At the end
            elif ' ' + measure.lower() + 's' in ings[i]:  # Space before measurement unit
                if ings[i][
                   -len(' ' + measure + 's'):] == ' ' + measure.lower() + 's':  # If measurement at end of string
                    ings[i] = ings[i].replace(' ' + measure.lower() + 's', '')
                    quantity[i].append(convert[measure])
                    found = True
                    break
            elif ' ' + measure.lower() in ings[i]:  # Space before measurement unit
                if ings[i][-len(' ' + measure):] == ' ' + measure.lower():  # If measurement at end of string
                    ings[i] = ings[i].replace(' ' + measure.lower(), '')
                    quantity[i].append(convert[measure])
                    found = True
                    break

        if not found:  # Didnt find a unit
            quantity[i].append('Unit')

        ings[i] = ings[i].strip()
    return ings, quantity


def check_preferences(user):
    # checks = {'excludes': [], 'similarity': 50, 'groups': 3, 'possible': 0, 'recommended': {},
    #           'rec_limit': 3, 'tastes': {}, 'ingredient_weights': json.dumps({}), 'sticky_weights': {},
    #           'recipe_ids': {}, 'menu_weight': 1, 'algorithm': 'Balanced'}
    # for preference in list(checks.keys()):
    #     if preference in user.harmony_preferences:
    #         checks[preference] = user.harmony_preferences[preference]
    # user.harmony_preferences = checks
    if user.extras == '' or user.extras is None:
        user.extras = []
    db.session.commit()


def add_follow(users):
    for user1 in users:
        for user2 in users:
            if user1.id != user2.id:
                follow = Followers(user_id=user1.id, follow_id=user2.id, status=1)
                db.session.add(follow)
    db.session.commit()


def generate_feed_contents(cards):
    # cards = sorted(friend_acts, key=lambda x: x.date_created, reverse=True)
    actions = []
    for act in cards:
        titles = act.titles  # Get titles of recipe in action from when that action was recorded
        rec_titles = {r.title: r.id for r in Recipes.query.filter(Recipes.id.in_(act.recipe_ids)).all()}
        for title1 in rec_titles:  # If recipe title changed or no longer exists handle it here
            for title2 in titles:
                if SequenceMatcher(a=title1, b=title2).ratio() > .8:  # New title is similar to old one
                    try:
                        titles.remove(title1)
                    except:
                        pass
        for title in titles:  # If recipe got deleted use its old title and dont link
            rec_titles[title] = None
        content = ''
        if act.type_ == 'Clear':
            content += 'ate '
            for i, title in enumerate(rec_titles):
                id_ = rec_titles[title]
                url = url_for('recipes.recipe_single', recipe_id=id_) if id_ is not None else '#'
                if len(rec_titles) == 1:
                    content += f'<a href="{url}">{title}</a>'
                elif i < len(rec_titles) - 1:
                    content += f'<a href="{url}">{title}, </a> '
                else:
                    content += f'and <a href="{url}">{title} </a>'
            content += ' this week!'
        elif act.type_ not in ['Update', 'Delete']:  # Borrow, Add, Unborrow
            title, id_ = list(rec_titles.items())[0]
            url = url_for('recipes.recipe_single', recipe_id=id_) if id_ is not None else '#'
            content += act.type_.lower() + 'ed '
            content += f'<a href="{url}">{title} </a>'
        else:  # Update, Delete
            title, id_ = list(rec_titles.items())[0]
            url = url_for('recipes.recipe_single', recipe_id=id_) if id_ is not None else '#'
            content += act.type_.lower() + 'd '
            content += f'<a href="{url}">{title} </a>'
        act.date_created.astimezone(pytz.timezone('US/Eastern'))
        card = {'user_id': act.user_id, 'content': content, 'date_created': act.date_created, 'type_': act.type_}
        actions.append(card)
    return actions


def get_friends(user):
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=user.id).all() if x.status == 1]
    followee_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    return followee_dict

# def get_friends(user):
#     # Get IDs of people the user follows, join with their User object, then return them in a dict
#     followees = Followers.query.filter_by(user_id=user.id, status=1).join(User, Followers.follow_id == User.id).all()
#     return {follow.follow_id: follow.followee for follow in followees}

# def get_friends(user):
#     followees = (
#         db.session.query(Followers.follow_id, User)
#         .join(User, Followers.follow_id == User.id)
#         .filter(Followers.user_id == user.id, Followers.status == 1)
#         .all()
#     )
#     return {follow_id: followee for follow_id, followee in followees}


def update_user_preferences(user, form, recommended, possible):
    preference = {key: user.harmony_preferences[key] for key in user.harmony_preferences}
    preference['similarity'] = form.similarity.data
    preference['groups'] = form.groups.data
    preference['recommended'] = {', '.join(list(group)): recommended[group] for group in recommended}
    preference['possible'] = possible
    user.harmony_preferences = preference
    db.session.commit()


def remove_menu_items(in_menu, recommended):
    in_menu = None if len(in_menu) < 1 else in_menu  # Don't show menu items in recommendation groups
    if in_menu is not None:
        for group in list(recommended.keys()):
            shortened = tuple(x for x in group if x not in in_menu)
            recommended[shortened] = recommended[group]
            del recommended[group]
    return recommended


def recipe_stack_w_args(recipe_list, preferences, form, in_menu, history_ex, recipe_hist):
    recipes = {r.title: r.quantity.keys() for r in recipe_list}
    count = int(form.groups.data)  # + len(in_menu) if form.groups.data else len(in_menu)
    recommended, possible = recipe_stack(recipes, count, max_sim=form.similarity.data,
                                         excludes=form.excludes.data + history_ex, includes=in_menu,
                                         limit=1_000_000, history=recipe_hist, **preferences)
    return recommended, possible


def load_harmonyform(current_user, form, in_menu, recipe_list, recipe_ex):
    in_menu = [recipe.title for recipe in in_menu]  # List of recipe titles in menu
    form.groups.choices = [x for x in range(2 - len(in_menu), 5) if 0 < x]
    modifier = current_user.harmony_preferences['modifier']
    form.similarity.choices = [(x, x) for x in range(0, 60, 10)] + [(float('inf'), 'No Limit')] if modifier == 'True' \
        else [(x, x) for x in range(50, 105, 5)] + [(float('inf'), 'No Limit')]
    form.similarity.default = [50, 50]
    # all_recipes =
    # print(recipe_list)
    # print(type(recipe_list))
    # recipe_list = recipe_list.items if isinstance(recipe_list, Pagination) else recipe_list
    excludes = [recipe.title for recipe in recipe_list if recipe.title not in (in_menu + recipe_ex)]
    form.excludes.choices = [x for x in zip([0] + excludes, ['-- select options (clt+click) --'] + excludes)]

    preferences = current_user.harmony_preferences  # Load user's previous preferences dictionary
    form.similarity.data = preferences['similarity']
    form.groups.data = preferences['groups']
    possible = preferences['possible']
    recommended = {}
    if preferences['recommended'] and preferences['recommended'] != '':  # If saved recommended is not empty
        recommended = {tuple(group.split(', ')): preferences['recommended'][group] for
                       group in preferences['recommended'] if tuple(group.split(', '))}
        # todo might be redundant, (prevent deleted recipes from being linked in a recommended)
        recommended = {key: value for key, value in recommended.items() if
                       all(x in [r.title for r in recipe_list] for x in key)}
    return form, recommended, recipe_ex, possible


def load_quantityform(recipe):
    data = {'ingredient_forms': [{'ingredient_quantity': recipe['quantity'][ingredient][0],
                                  'ingredient_type': recipe['quantity'][ingredient][1],
                                  'ingredient_name': ingredient}
                                 for ingredient in recipe['quantity'].keys()]}
    form = FullQuantityForm(data=data)
    form.ingredients = [x for x in recipe['quantity'].keys()]
    return form


def trend_sort(item):
    try:
        value = item.times_eaten / (datetime.utcnow() - item.date_created).days
    except ZeroDivisionError:
        value = 0
    return value


class Pagination(object):
    def __init__(self, page, per_page, all_items):
        #: the current page number (1 indexed)
        self.page = page
        #: the number of items to be displayed on a page.
        self.per_page = per_page
        if isinstance(all_items, list):  # Not paginated yet
            self.all_items = all_items  # List of items
            #: the total number of items matching the query
            self.total = len(all_items)
            #: the fake pagination object
            self.items_dict = {}
            for i in range(self.pages):  # Create dictionary of lists, keys are pages
                self.items_dict[i] = all_items[per_page * i:per_page * (i + 1)]
        elif isinstance(all_items, dict):  # Changing pages initializes new Pagination with old dict and diff page items
            self.items_dict = all_items
        else:
            raise Exception
        #: the items for the current page
        self.items = self.items_dict[page - 1]

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.items_dict is not None, 'a non empty dictionary is required ' \
                                            'for this method to work'
        return Pagination(self.page - 1, self.per_page, self.items_dict)

    @property
    def prev_num(self):
        """Number of the previous page."""
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.items_dict is not None, 'a non empty dictionary is required ' \
                                            'for this method to work'
        return Pagination(self.page + 1, self.per_page, self.items_dict)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if not self.has_next:
            return None
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        """
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or (
                    num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def borrow_sort(item):
    count = User_Rec.query.filter_by(recipe_id=item.id, borrowed=True).count()
    return count


def paginate_sort(view='', sort='alpha', type_='all', search=None, friend_choice=[], per=15,  # todo add asc or desc
                  page=1):  # Sorts, filters and paginates, returning a paginate object
    in_menu, recipe_ids = None, {}  # todo Generators instead?
    borrows = {x.recipe_id: x.in_menu for x in
               User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}  # {Borrowed_id: bool(in_menu)}
    view_dict = {'friends': Recipes.user_id.in_(friend_choice),
                 'public': and_(Recipes.user_id.isnot(None), Recipes.public.is_(True)),
                 'self': Recipes.user_id.is_(current_user.id)}
    sort_dict = {'date': Recipes.date_created.desc(), 'eaten': Recipes.times_eaten.desc(),
                 'alpha': Recipes.title.asc(), 'none': Recipes.title.asc(),
                 'hot': (Recipes.times_eaten / (datetime.now()-Recipes.date_created)).desc()}
    search_q = Recipes.title.isnot(None) if search is None else \
        or_(Recipes.title.contains(search), Recipes.recipe_genre.contains(search))
    types_q = Recipes.recipe_type.isnot(None) if (type_ == 'all') else Recipes.recipe_type.is_(type_)
    view_q, sort_q = view_dict[view], sort_dict.get(sort, None)  # hot/borrow sorting may need separate

    if sort in sort_dict:
        borrow_filter = Recipes.id.in_(borrows)  # User's borrowed recipes
        recipe_list = Recipes.query.filter(or_(and_(view_q, search_q, types_q), borrow_filter)).order_by(sort_q). \
            paginate(page=page, per_page=per)
    else:
        # 1. id_borrowed_tuples = User_Rec.query.with_entities(User_Rec.recipe_id).filter_by(borrowed=True).group_by(
        # User_Rec.recipe_id).order_by(func.count(User_Rec.recipe_id).desc()).all() # join to Rec by (id, num_borrowed)
        # 2. Recipes.query.join(User_Rec, func.count(User_Rec.recipe_id).label('times_borrowed')).
        # order_by(Recipes.times_borrowed).all()
        # 3. SELECT id, times_borrowed from recipes JOIN (SELECT user__rec.recipe_id AS user__rec_recipe_id,
        # count(user__rec.recipe_id) AS times_borrowed FROM user__rec WHERE user__rec.borrowed = 1 GROUP BY
        # user__rec.recipe_id) AS b ON user__rec_recipe_id ORDER BY b.times_borrowed;
        borrowed_rec_ids = [x for (x,) in  # distinct() vs no .distinct and set()
                            User_Rec.query.with_entities(User_Rec.recipe_id).filter_by(borrowed=True).distinct()]
        borrow_filter = Recipes.id.in_(borrowed_rec_ids)  # Recipes with row(s) in User_Rec (borrows > 0)
        recipe_list = Recipes.query.filter(and_(view_q, search_q, types_q, view_q, borrow_filter)).all()
        recipe_list = sorted(recipe_list, key=lambda x: borrow_sort(x), reverse=True)  # Order by number borrowed
        recipe_list = Pagination(page=page, per_page=per, all_items=recipe_list)  # Custom pagination object
    if (sort == 'none') and (view == 'self'):  # User didnt want to sort, keep in_menu on top
        in_menu = Recipes.query.filter_by(author=current_user, in_menu=True).all()
        in_menu = in_menu + Recipes.query.filter(Recipes.id.in_([x for x in borrows.keys() if borrows[x]])).all()
        i = 0
        for recipe in in_menu:  # Puts menu items first in recipe_list
            try:
                recipe_list.items.remove(recipe)
            except ValueError:  # Flask Paginate object: can't remove recipe (& put on top) if not on first page
                continue
            recipe_list.items.insert(i, recipe)
            i += 1
        recipe_ids = {recipe.title: recipe.id for recipe in recipe_list.items}
    count = recipe_list.total
    return recipe_list, count, in_menu, borrows, recipe_ids


def add_eatens():
    all_users = User.query.all()
    for user in all_users:
        user_history = [item for sublist in user.history for item in sublist]
        if user_history:
            counts = dict()
            for i in user_history:
                counts[i] = counts.get(i, 0) + 1
            for key in counts:
                recipe = Recipes.query.filter_by(id=key).first()
                if recipe is not None:
                    if recipe in user.recipes:
                        recipe.times_eaten = counts[key]
                    else:
                        recipe = User_Rec.query.filter_by(recipe_id=key, user_id=user.id).first()
                        if recipe is not None:
                            recipe.times_eaten = counts[key]
            # db.session.commit()


def convert_history():
    all_users = User.query.all()
    for user in all_users:
        user_history = user.history
        if user_history:  # There are entries
            Dict = {}
            now = datetime.utcnow()
            now = now - timedelta(days=2)  # days
            for list_ in user_history:
                Dict[now] = list_
                now = now - timedelta(days=7)
        else:
            user_history = {}
    # db.session.commit()

# @recipes.route('/recipes/<int:recipe_id>/download', methods=['GET', 'POST'])
# @login_required
# def export(recipe_id):
#     recipe_post = Recipes.query.get_or_404(recipe_id)
#     if recipe_post.author != current_user:
#         abort(403)
#     else:
#         title = recipe_post.title
#         recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
#         return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
#                                                                      f"attachment; filename={title}.txt"})
#     return redirect(url_for('recipe_single', recipe_id=recipe_id))


# def transfer_site_changes():
#     for recipe in Recipes.query.all():
#         recipe.quantity = {' '.join([word.capitalize() for word in ingredient.split(' ')]): [1, 'Unit']
#                            for ingredient in recipe.content.split(', ')}
#         recipe.title = ' '.join([word.capitalize() for word in recipe.title.split(' ')])
#     for user in User.query.all():
#         user.harmony_preferences = {'excludes': [], 'similarity': 50, 'groups': 3, 'possible': 0, 'recommended': {},
#                                     'rec_limit': 3, 'tastes': {}, 'ing_gen_weights': {}, 'ing_pair_weights': {},
#                                     'recipe_ids': {}, 'menu_weight': 1}
#          user.extras = []
#     for aisle in Aisles.query.all():
#         aisle.content = ', '.join([' '.join([word.capitalize() for word in ingredient.split(' ')])
#                                    for ingredient in aisle.content.split(', ')])
#         aisle.title = ' '.join([word.capitalize() for word in aisle.title.split(' ')])
#         aisle.store = ' '.join([word.capitalize() for word in aisle.store.split(' ')])
#
# cast(Recipes.times_eaten, FLOAT) /
#                         cast(func.extract('epoch', datetime.now()) - func.extract('epoch', Recipes.date_created),
#                              FLOAT).desc()
# 1.0 * Recipes.times_eaten / ((func.extract('epoch', datetime.now()) -
#                                                       func.extract('epoch', Recipes.date_created)) / 60.0).desc()




# @recipes.route('/remove_duplicates', methods=['GET', 'POST'])
# @login_required
# def remove_duplicates():
#     if not current_user.is_authenticated:
#         return redirect(url_for('main.landing'))
#     user_recipes = Recipes.query.filter_by(user_id=3).all()
#     if request.method == 'GET':
#         ingredients = [[y for y in x.quantity.keys()] for x in user_recipes]
#         ingredients = set([item for sublist in ingredients for item in sublist])
#         suggested_changes = {}
#         for i, ing1 in enumerate(ingredients):
#             suggested_changes[ing1] = []
#             for j, ing2 in enumerate(ingredients):
#                 if (not i == j) and (SequenceMatcher(a=ing1, b=ing2).ratio() > 0.7):
#                     suggested_changes[ing1].append(ing2)
#         suggested_changes = {k: v for k, v in suggested_changes.items() if v}
#
#         entries = []
#         for ing, suggestions in sorted(suggested_changes.items(), key=lambda x: x[0]):
#             form = SimplifyIngredientForm()
#             form.ingredient_name.data = ing
#             form.suggested.choices = [(None, 'Keep Ingredient')] + [(x, x) for x in suggestions]
#             entries.append(form)
#     else:
#         returned = [x[1] for x in request.form.lists()if x[0]!='csrf_token']
#         ing_changes = {x: z for x, z in zip(*returned) if z != 'None'}
#         swap_ings(user_recipes, ing_changes)
#         entries = []
#     return render_template('ingredient_simplifier.html', title='Simplify', entries=entries,
#                            legend='Remove Duplicate Ingredients')

# @recipes.route('/linked_user/<int:new_user>', methods=['GET', 'POST'])
# @login_required
# def linked_user():
# followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
# friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
# cards = sorted(Actions.query.filter(Actions.user_id.in_(followees)).all(), key=lambda x: x.date_created, reverse=True)
# # Get friend recipe dict(id:Recipe) to hyperlink their 'Clear' actions
# recs = [item for sublist in [r.recipe_ids for r in cards] for item in sublist]
# recs = Recipes.query.filter(Recipes.id.in_(recs)).all()
# rec_dict = {r.id: r for r in recs}
# title_dict = {v.title: k for k, v in rec_dict.items()}
# all_friend_recs = {x.id: x for x in Recipes.query.filter(Recipes.user_id.in_(followees)).all()}
# return render_template('friend_feed.html', rec_dict=rec_dict, cards=cards, title='Friend Feed', sidebar=True, #search=None
#                        colors=colors, friend_dict=friend_dict, all_friends=friend_dict, friends=True, feed=True,
#                        all_friend_recs=all_friend_recs, title_dict=title_dict)

# elif recipe_post.user_id == current_user.id:
#     title = recipe_post.title
#     recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
#     return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
#                                                              f"attachment; filename={title}.txt"})


"""
Guidelines for a better GroceryHero:
Omit units of measure from ingredient names:
Canned pineapple would be pineapple with "canned" as the measurement.
Omit preparation details from ingredient names:
Use ingredient names that specify what to buy. For example: orange peel and orange would require purchasing the same 
ingredient in a grocery store but orange would allow others to better find your recipe and producing a better grocery 
list while 'orange peel' is a preparation detail you would add to the 'prep' section like 'minced' would for 
'minced garlic'. Same for lemon vs lemon zest. However sugar is different than powdered sugar as is milk vs 
evaporated milk or onion and red onion, pineapple vs pineapple rings, vegan parmesan cheese vs parmesan cheese.

Omit plural ingredients if it makes sense.
Foods that are considered a whole serving are generally singular such as a peach. Beans would be plural since one would
not generally eat one bean. A sausage link could be eaten as a single serving. If you are still unsure, whether you
can buy just one of an item can be another guide. Chocolate chips are numerous in a package so you would make it plural. 
"""

"""
import string
from GroceryHero.Recipes.utils import parse_ingredients
from GroceryHero.Users.utils import save_picture
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode
from GroceryHero.models import Recipes
from GroceryHero import db, create_app
db.app = create_app()


def recipe_from_link(link):  # page where user enters url
    try:
        scraper = scrape_me(link)
    except WebsiteNotImplementedError:
        try:
            scraper = scrape_me(link, wild_mode=True)
        except NoSchemaFoundInWildMode:
            return {}
    ingredients = [x.lower() for x in scraper.ingredients()]
    ings, quantity = parse_ingredients(ingredients)
    ings = [string.capwords(x.strip()) for x in ings if x.strip() != '']
    im_path = scraper.image()
    quantity = {ingredient: [Q, M] for ingredient, (Q, M) in zip(ings, quantity)}
    # servings = scraper.yields()
    prep_time = scraper.total_time()
    recipe_dict = {'title': scraper.title(), 'notes': scraper.instructions(),
                   'quantity': quantity, 'link': link, 'im_path': im_path, 'prep_time': prep_time}
    return recipe_dict


def zuck(recipe):  # If recipe is not empty
    title = recipe['title']
    quantity = recipe['quantity']
    notes = recipe['notes']
    prep_time = float(recipe['prep_time']) if recipe['prep_time'] != 0 else None
    prep_time = {'total': int(prep_time)} if ((prep_time is not None) and prep_time.is_integer()) else prep_time
    rtype = 'Dinner'
    link = recipe.get('link', '')
    pic_fn = save_picture(recipe.get('im_path', None), 'static/recipe_pics', download=True)
    pic_fn = pic_fn if pic_fn is not None else 'default.png'
    recipe = Recipes(title=title, quantity=quantity, user_id=14,
                     notes=notes, recipe_type=rtype, link=link,
                     picture=pic_fn, public=True, prep_time=prep_time, credit=False)
    return recipe


def zuckRecipes(start=6_663, end=26_894):
    site = 'https://www.allrecipes.com/recipe/'
    start = 13884
    for i in range(start, end):
        try:
            recipe = recipe_from_link(site+str(i)+'/')  # Returns dict
            if recipe:  #
                recipe = zuck(recipe)
                db.session.add(recipe)
            else:
                print(i)
            if (i % 10) == 0:
                db.session.commit()
                # recipe.originator = recipe.id
                # db.session.commit()
        except Exception as e:
            print(e)

with db.app.app_context():
    zuckRecipes()
    
    
for recipe in db.session.query(Recipes).all():
    recipe.public = True
db.session.commit()


for recipe in db.session.query(Recipes).all():
    if (recipe.prep_time is not None) and recipe.prep_time:
        recipe.prep_time = recipe.prep_time['total']
db.session.commit()

"""

