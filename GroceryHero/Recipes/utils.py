from datetime import datetime, timedelta
from difflib import SequenceMatcher
import pytz
from flask import url_for
from flask_login import current_user
from sqlalchemy import or_, and_
from math import ceil
from GroceryHero import db
from GroceryHero.HarmonyTool import recipe_stack
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
    Measure_dict = Dict_func()

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
            if (self.type == 'Generic') and (self.unit != other.unit):
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

    def convert_to_str(self, system=False, type_=False):
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
        if self.type == 'Generic':
            total = self.value + other.value
            return Measurements(round(total, rounding), unit=self.unit)
        value1 = self.Convert[self.unit] * self.value  # convert to lowest
        value2 = other.Convert[other.unit] * other.value  # convert to lowest
        total = value1 + value2
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric_system else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    self.unit = volume
                    return Measurements(round(total, 2), unit=volume)
        elif self.type == 'Weight':
            weights = self.Metric_Weights if self.metric_system else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    self.unit = weight
                    return Measurements(round(total, 2), unit=weight)
        return Measurements(round(total, 2), unit=self.unit)  # todo does this unit always work?

    def __sub__(self, other, rounding=2):
        self.compatible(other, error=True)
        if self.type == 'Generic':
            total = self.value + other.value
            return Measurements(round(total, rounding), unit=self.unit)
        value1 = self.Convert[self.unit] * self.value  # convert to lowest
        value2 = other.Convert[other.unit] * other.value  # convert to lowest
        total = value1 - value2
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric_system else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    self.unit = volume
                    return Measurements(round(total, 2), unit=volume)
        elif self.type == 'Weight':
            weights = self.Metric_Weights if self.metric_system else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    self.unit = weight
                    return Measurements(round(total, 2), unit=weight)
        return Measurements(round(total, 2), unit=self.unit)

    def __repr__(self):
        unit = self.unit + 's' if self.value != 1 else self.unit
        return f'Measure({self.name}: {self.value} {unit})'


from GroceryHero.Recipes.forms import FullQuantityForm


def parse_ingredients(ingredients):
    specials = {'¼': '1/4', '½': '1/2', '¾': '3/4', '⅐': '1/7', '⅑': '1/9', '⅒': '1/10', '⅓': '1/3', '⅔': '2/3',
                '⅕': '1/5', '⅖': '2/5', '⅗': '3/6', '⅘': '4/5', '⅙': '1/6', '⅚': '5/6', '⅛': '1/8', '⅜': '3/8',
                '⅝': '5/8', '⅞': '7/8'}
    measures = Measurements.Measures
    extras = ['cup', 'tablespoon', 'teaspoon', 'fluid ounce', 'tsp', 'tbsp', 'oz', 'lb', 'mg', 'fl oz', 'ml', 'g'] # todo Make sure that a space is after the measurement
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
            elif ' '+measure.lower()+'s' in ings[i]:  # Space before measurement unit
                if ings[i][-len(' '+measure+'s'):] == ' '+measure.lower()+'s':   # If measurement at end of string
                    ings[i] = ings[i].replace(' ' + measure.lower() + 's', '')
                    quantity[i].append(convert[measure])
                    found = True
                    break
            elif ' '+measure.lower() in ings[i]:  # Space before measurement unit
                if ings[i][-len(' '+measure):] == ' '+measure.lower():  # If measurement at end of string
                    ings[i] = ings[i].replace(' '+measure.lower(), '')
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
                    titles.remove(title1)
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
    return followees, followee_dict


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


def borrow_sort(item):
    count = User_Rec.query.filter_by(recipe_id=item.id, borrowed=True).count()
    return count


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
                self.items_dict[i] = all_items[per_page*i:per_page*(i+1)]
        elif isinstance(all_items, dict):  # Changing pages initializes new Pagination with old dict and diff page items
            self.items_dict = all_items
        else:
            raise Exception
        #: the items for the current page
        self.items = self.items_dict[page-1]

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
            if num <= left_edge or (num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def paginate_sort(view='', sort='alpha', type_='all', search=None, friend_choice=None, per=15,  # todo add asc or desc
                  page=1):  # Sorts, filters and paginates, returning a paginate object
    in_menu, recipe_ids = None, {}  # todo Generators instead?
    borrows = {x.recipe_id: x.in_menu for x in
               User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}  # {Borrowed_id: bool(in_menu)}
    view_dict = {'friends': Recipes.user_id.in_(friend_choice),
                 'public': Recipes.user_id.isnot(None),
                 # and_(Recipes.public.is_(True), Recipes.user_id.isnot(None)) exclude self?
                 'self': Recipes.user_id.is_(current_user.id)}
    sort_dict = {'date': Recipes.date_created.desc(), 'eaten': Recipes.times_eaten.desc(),
                 'alpha': Recipes.title.asc(), 'none': Recipes.title.asc()}

    search_q = Recipes.title.isnot(None) if search is None else \
        and_(Recipes.title.contains(search), Recipes.recipe_genre.contains(search))
    types_q = Recipes.recipe_type.isnot(None) if (type_ == 'all') else Recipes.recipe_type.is_(type_)
    view_q, sort_q = view_dict[view], sort_dict.get(sort, None)  # hot/borrow sorting may need separate

    if sort in sort_dict:
        recipe_list = Recipes.query.filter(and_(view_q, search_q, types_q, view_q)). \
            order_by(sort_q).paginate(page=page, per_page=per)
    else:
        recipe_list = Recipes.query.filter(and_(view_q, search_q, types_q, view_q)).all()
        sorting = borrow_sort if sort == 'borrow' else trend_sort
        recipe_list = sorted(recipe_list, key=lambda x: sorting(x), reverse=True)
        recipe_list = Pagination(page=page, per_page=per, all_items=recipe_list)  # Custom pagination object

    if (sort == 'none') and (view == 'self'):  # User didnt want to sort, keep in_menu on top
        in_menu = Recipes.query.filter_by(author=current_user, in_menu=True).all()
        in_menu = in_menu + Recipes.query.filter(Recipes.id.in_([x for x in borrows.keys() if borrows[x]])).all()
        for i, recipe in enumerate(in_menu):  # Puts menu items first in recipe_list
            recipe_list.items.remove(recipe)
            recipe_list.items.insert(i, recipe)
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


# for recipe in Recipes.query.all():
#     recipe.quantity = {' '.join([word.capitalize() for word in ingredient.split(' ')]): [1, 'Unit']
#                        for ingredient in recipe.content.split(', ')}
#     recipe.title = ' '.join([word.capitalize() for word in recipe.title.split(' ')])
# for user in User.query.all():
#     user.harmony_preferences = {'excludes': [], 'similarity': 50, 'groups': 3, 'possible': 0, 'recommended': {},
#                                 'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {},
#                                 'recipe_ids': {}, 'menu_weight': 1}
#     user.extras = []
# for aisle in Aisles.query.all():
#     aisle.content = ', '.join([' '.join([word.capitalize() for word in ingredient.split(' ')])
#                                for ingredient in aisle.content.split(', ')])
#     aisle.title = ' '.join([word.capitalize() for word in aisle.title.split(' ')])
#     aisle.store = ' '.join([word.capitalize() for word in aisle.store.split(' ')])

#     case_dict = {('friends', 'hot', 'all'): None, ('friends', 'date', 'all'): None,
#                  ('friends', 'eaten', 'all'): None, ('friends', 'alpha', 'all'): None,
#                  ('friends', 'borrow', 'all'): None,
#                  ('self', 'hot', 'all'): None, ('self', 'date', 'all'): None,
#                  ('self', 'eaten', 'all'): None, ('self', 'alpha', 'all'): None,
#                  ('self', 'borrow', 'all'): None,
#                  ('public', 'hot', 'all'): None, ('public', 'date', 'all'): None,
#                  ('public', 'eaten', 'all'): None, ('public', 'alpha', 'all'): None,
#                  ('public', 'borrow', 'all'): None,
#
#                  ('friends', 'hot'): None, ('friends', 'date'): None,
#                  ('friends', 'eaten'): None, ('friends', 'alpha'): None,
#                  ('friends', 'borrow'): None,
#                  ('self', 'hot'): None, ('self', 'date'): None,
#                  ('self', 'eaten'): None, ('self', 'alpha'): None,
#                  ('self', 'borrow'): None,
#                  ('public', 'hot'): None, ('public', 'date'): None,
#                  ('public', 'eaten'): None, ('public', 'alpha'): None,
#                  ('public', 'borrow'): None,
#
#                  ('friends', 'hot', 'all', True): None, ('friends', 'date', 'all', True): None,
#                  ('friends', 'eaten', 'all', True): None, ('friends', 'alpha', 'all', True): None,
#                  ('friends', 'borrow', 'all', True): None,
#                  ('self', 'hot', 'all', True): None, ('self', 'date', 'all', True): None,
#                  ('self', 'eaten', 'all', True): None, ('self', 'alpha', 'all', True): None,
#                  ('self', 'borrow', 'all', True): None,
#                  ('public', 'hot', 'all', True): None, ('public', 'date', 'all', True): None,
#                  ('public', 'eaten', 'all', True): None, ('public', 'alpha', 'all', True): None,
#                  ('public', 'borrow', 'all', True): None,
#
#                  ('friends', 'hot', True): None, ('friends', 'date', True): None,
#                  ('friends', 'eaten', True): None, ('friends', 'alpha', True): None,
#                  ('friends', 'borrow', True): None,
#                  ('self', 'hot', True): None, ('self', 'date', True): None,
#                  ('self', 'eaten', True): None, ('self', 'alpha', True): None,
#                  ('self', 'borrow', True): None,
#                  ('public', 'hot', True): None, ('public', 'date', True): None,
#                  ('public', 'eaten', True): None, ('public', 'alpha', True): None,
#                  ('public', 'borrow', True): None}
        # if sort in ['date', 'eaten']:
        #     sorting = Recipes.date_created.desc() if sort == 'date' else Recipes.times_eaten.desc()
        #     recipe_list = Recipes.query.filter((Recipes.recipe_type.is_(types))).order_by(sorting).paginate(
        #         page=page, per_page=per) if types != 'all' else \
        #         Recipes.query.order_by(sorting).paginate(page=page, per_page=per)
        # elif sort in ['hot', 'borrow']:
        #     recipe_list = Recipes.query.filter((Recipes.recipe_type.is_(types))).paginate(
        #         page=page, per_page=per) if types != 'all' else Recipes.query.paginate(page=page, per_page=per)
        #     if sort == 'hot':  # Eaten//date
        #         recipe_list.items = sorted(recipe_list.items, key=lambda x: date_sort(x), reverse=True)
        #     else:  # Most borrowed
        #         all_borrowed = User_Rec.query.filter_by(borrowed=True).all()  # currently borrowed
        #         all_borrowed = [x.recipe_id for x in all_borrowed]
        #         recipe_list.items = sorted(recipe_list.items, key=lambda x: all_borrowed.count(x.id), reverse=True)
        # else:  # Date
        #     sorting = Recipes.date_created.desc()
        #     recipe_list = Recipes.query.order_by(sorting).paginate(page=page, per_page=per)

    # if (search is not None) and (search not in ['Recipe Options', '']):
    #     recipe_list.items = [recipe for recipe in recipe_list.items if search.lower() in recipe.title.lower()
    #                          or search.lower() in recipe.quantity.keys()]
    # if sort == 'hot':  # Eaten//date
    #     recipe_list.items = sorted(recipe_list.items, key=lambda x: date_sort(x), reverse=True)
    # else:  # Most borrowed
    #     recipe_list.items = sorted(recipe_list.items, key=lambda x: all_borrowed.count(x.id), reverse=True)
    # if view == 'friends':
    #     all_friends = list(friend_choice)  # Friend_choice is all friends if no specific friend was chosen
    #     friends_q = Recipes.user_id.in_(all_friends)
    #     if sort in sort_dict:
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q, friends_q)). \
    #             order_by(sort_dict[sort]).paginate(page=page, per_page=per)  # Get all recipes
    #     elif sort == 'borrow':  # Trending sort or Borrow sort
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q, friends_q)). \
    #             order_by(Recipes.times_borrowed).paginate(page=page, per_page=per)  # Get all recipes
    #         # recipe_list = recipe_list.paginate(page=page, per_page=per)
    #         # print(recipe_list.items)
    #         # print(len(recipe_list.items))
    #         # recipe_list.items = sort_dict[sort](recipe_list)  # Only sorts per page
    #         # print(recipe_list.items)
    #     else:  # todo hot
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q, friends_q)). \
    #             order_by(Recipes.trend_index).paginate(page=page, per_page=per)  # Get all recipes
    #     count = recipe_list.count()
    # elif view == 'public':
    #     count = Recipes.query.filter(Recipes.user_id.isnot(current_user.id)).count()  # todo and that are public
    #     if sort in sort_dict:
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q)). \
    #             order_by(sort_dict[sort]).paginate(page=page, per_page=per)  # Get all recipes
    #     elif sort == 'borrow':  # Borrow or Trending
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q)).\
    #             order_by(Recipes.times_borrowed).paginate(page=page, per_page=per)
    #         # recipe_list.items = sort_dict[sort](recipe_list)
    #     else:
    #         recipe_list = Recipes.query.filter(
    #             and_(Recipes.public.is_(True), search_q, types_q)). \
    #             order_by(Recipes.trend_index).paginate(page=page, per_page=per)
    # else:  # Your own recipes (including incorrect given view)
    #     if sort in sort_dict:
    #         # Own recipes, all types, with all borrows, with search term, and ordered
    #         recipe_list = Recipes.query.filter(
    #             and_(or_(Recipes.author == user, Recipes.id.in_(borrows.keys()))), search_q, types_q).\
    #             order_by(sort_dict[sort]).paginate(page=page, per_page=per)  # Get all recipes
    #     elif sort == 'borrow':  # todo Most borrowed
    #         print(3)
    #         recipe_list = Recipes.query.filter(
    #             and_(or_(Recipes.author == user, Recipes.id.in_(borrows.keys()))), search_q, types_q). \
    #             order_by(Recipes.times_borrowed).paginate(page=page, per_page=per)  # Get all recipes
    #     else:  # todo Hot/Trending
    #         print(4)
    #         recipe_list = Recipes.query.filter(
    #             and_(or_(Recipes.author == user, Recipes.id.in_(borrows.keys()))), search_q, types_q). \
    #             order_by(Recipes.trend_index).paginate(page=page, per_page=per)  # Get all recipes