import itertools
import json
import os
import secrets
import shutil
import string

import requests
from PIL import Image
from flask import url_for, current_app, flash
from flask_login import current_user
from flask_mail import Message
from werkzeug.utils import redirect
from werkzeug.datastructures import FileStorage
from GroceryHero import mail, db
from GroceryHero.Recipes.forms import Measurements
from GroceryHero.models import Aisles, Recipes


def save_picture(form_picture, filepath='static/profile_pics', download=False):
    if form_picture is None:
        return None
    random_hex = secrets.token_hex(8)
    if download:
        url = form_picture
        r = requests.get(url, stream=True)
        if r.status_code == 200:  # Downloaded
            _, f_ext = os.path.splitext(url)
            r.raw.decode_content = True  # Decode_content otherwise file size will be zero
            form_picture = r.raw
        else:  # Not downloaded
            return None
    else:
        _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, filepath, picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreply@GroceryHero.com', recipients=[user.email])
    msg.body = f"""To reset your password visit the following link:
{url_for('users.reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no change will be made.
"""
    mail.send(msg)


def import_files(file, import_type):
    try:
        imports = json.loads(file.read())
        if import_type == 'recipes':
            all_current = [recipe.title for recipe in Recipes.query.filter_by(author=current_user).all()]
        elif import_type == 'aisles':
            all_current = [aisle.title for aisle in Aisles.query.filter_by(author=current_user).all()]
        else:
            return redirect(url_for('users.account'))
        # print(all_current)
        index, dup = 0, 0
        if import_type == 'recipes':
            for recipe in imports:
                contents = imports[recipe]
                quantity = {string.capwords(ingredient.strip()):
                                contents[0][ingredient] if contents[0][ingredient][1] in Measurements.Measures else
                                [contents[0][ingredient][0], 'Unit'] for ingredient in contents[0]}
                recipe = Recipes(title=string.capwords(recipe.strip()), quantity=quantity, notes=contents[-1],
                                 author=current_user)
                if recipe.title in all_current:
                    del recipe
                    dup += 1
                else:
                    db.session.add(recipe)
                    index += 1
        else:
            for aisle in imports:
                contents = imports[aisle]
                ingredients = ', '.join([string.capwords(x.strip()) for x in contents[0].split(', ')])
                aisle = Aisles(title=string.capwords(aisle.strip()), content=ingredients, store=contents[1],
                               author=current_user)
                if aisle not in all_current:
                    db.session.add(aisle)
                    index += 1
                else:
                    dup += 1
        db.session.commit()
        dup = f'{dup} duplicates' if dup > 1 else f'{dup} duplicate'
        flash(f'Import successful ({index} recipes added, {dup})', 'success')
    except Exception as e:
        print(e)
        flash('Import unsuccessful', 'danger')
    return redirect(url_for('users.account'))


def load_harmony_form(form, user):
    recipes = Recipes.query.filter_by(author=current_user).all()
    ingredients = [recipe.quantity.keys() for recipe in recipes]
    ingredients = sorted(set([item for sublist in ingredients for item in sublist]))
    # Recommendation number
    form.recommend_num.data = user.harmony_preferences['rec_limit']
    # Recipe pair weights
    form.pairs.choices = [(x, x) for x in (['--select options (ctl+click)--'] +
                                           sorted(set([recipe.title for recipe in recipes])))]
    # Ingredient weights
    form.ingredient.choices = [(x, x) for x in (['--select options (ctl+click)--'] + ingredients)]
    # Sticky weights
    form.ingredient2.choices = [(x, x) for x in (['--select options (ctl+click)--'] + ingredients)]
    # Exclude ingredients
    current_excludes = user.harmony_preferences['ingredient_excludes']
    form.ingredient_ex.choices = [(x, x) for x in (['--select options (ctl+click)--'] +
                                                   ingredients) if x not in current_excludes]
    form.ingredient_rem.choices = [(x, x) for x in ['--to put back (ctl+click)--'] +
                                   [item for item in current_excludes]]
    # Algorithm
    form.algorithm.data = user.harmony_preferences['algorithm']
    # Modifier
    form.modifier.data = user.harmony_preferences['modifier']
    return form


def update_harmony_preferences(form, user):  # Do dictionaries need to be JSON?
    dictionary = user.harmony_preferences.copy()
    dictionary['rec_limit'] = form.recommend_num.data
    dictionary['algorithm'] = form.algorithm.data
    dictionary['modifier'] = form.modifier.data
    # Ingredient weights
    if isinstance(dictionary['ingredient_weights'], str):  # Load old (If the entries are JSON for some reason?)
        dictionary['ingredient_weights'] = json.loads(dictionary['ingredient_weights'])
    if 'Ingredients' not in form.ingredient.data:  # User adds new item(s)
        for ingredient in form.ingredient.data:  # For item in multi-select
            if ingredient not in dictionary['ingredient_weights']:  # Not in preferences yet
                if float(form.ingredient_weights.data) == 1:  # Don't add redundant weight
                    pass
                else:
                    dictionary['ingredient_weights'][ingredient] = str(form.ingredient_weights.data)
            else:  # Weight is changing
                if float(form.ingredient_weights.data) == 1:  # Remove from preferences since redundant
                    del dictionary['ingredient_weights'][ingredient]
                else:  # Else change the weight
                    dictionary['ingredient_weights'][ingredient] = str(form.ingredient_weights.data)
        dictionary['ingredient_weights'] = json.dumps(dictionary['ingredient_weights'])  # Modify dic with changes
    # Recipe pairs
    if isinstance(dictionary['tastes'], str):  # If the entries are JSON for some reason?
        dictionary['tastes'] = json.loads(dictionary['tastes'])
    if '--select options (ctl+click)--' not in form.pairs.data and len(form.pairs.data) > 1:
        for combo in itertools.combinations(form.pairs.data, 2):
            combo = str(str(combo[0]) + ', ' + str(combo[1]))
            if combo not in dictionary['tastes']:  # Not in preferences yet
                if float(form.pair_weight.data) == 1.0:  # Don't add redundant weight
                    pass
                else:
                    dictionary['tastes'][combo] = str(form.pair_weight.data)
                    # print(dictionary['tastes'])
            else:  # Weight is changing
                if float(form.pair_weight.data) == 1.0:  # Remove from preferences since redundant
                    del dictionary['tastes'][combo]
                else:  # Else change the weight
                    dictionary['tastes'][combo] = str(form.pair_weight.data)
        dictionary['tastes'] = json.dumps(dictionary['tastes'])  # todo why dump here and load earlier?
        # print(dictionary['tastes'])
    # Sticky weights
    if isinstance(dictionary['sticky_weights'], str):  # Load old
        dictionary['sticky_weights'] = json.loads(dictionary['sticky_weights'])
    if '--select options (ctl+click)--' not in form.ingredient2.data:
        for ingredient in form.ingredient2.data:
            if ingredient not in dictionary['sticky_weights']:
                if float(form.sticky_weights.data) == 0:
                    pass
                else:
                    dictionary['sticky_weights'][ingredient] = str(form.sticky_weights.data)
            else:  # Weight is changing
                if float(form.sticky_weights.data) == 0:  # Remove from preferences since redundant
                    del dictionary['sticky_weights'][ingredient]
                else:  # Else change the weight
                    dictionary['sticky_weights'][ingredient] = str(form.sticky_weights.data)
        dictionary['sticky_weights'] = json.dumps(dictionary['sticky_weights'])
    # Ingredient excludes (or undoing exclude)
    if '--select options (ctl+click)--' not in form.ingredient_ex.data:
        dictionary['ingredient_excludes'] = dictionary['ingredient_excludes'] + form.ingredient_ex.data
    if '--select options (ctl+click)--' not in form.ingredient_rem.data:
        dictionary['ingredient_excludes'] = [x for x in dictionary['ingredient_excludes'] if
                                             x not in form.ingredient_rem.data]
    user.harmony_preferences = dictionary


def import_recipes_terminal(recipe_dictionary, user, database):
    all_current = [recipe.title for recipe in Recipes.query.filter_by(author=user).all()]
    index, dup = 0, 0
    for recipe in recipe_dictionary:
        contents = recipe_dictionary[recipe]
        quantity = {string.capwords(ingredient.strip()):
                    contents[0][ingredient] if contents[0][ingredient][1] in Measurements.Measures else
                    [contents[0][ingredient][0], 'Unit'] for ingredient in contents[0]}
        recipe = Recipes(title=string.capwords(recipe.strip()), quantity=quantity, notes=contents[-1],
                         author=user)
        if recipe.title in all_current:
            dup += 1
        else:
            database.session.add(recipe)
            index += 1
    database.session.commit()


def starter_recipes():
    recipes = []
    recipes.append(Recipes(title='Hamburgers', quantity={'Beef': ['1', 'Pound'], 'Buns': ['1', 'Package'], 'Ketchup': ['3', 'US Tablespoon']}, author=current_user))
    recipes.append(Recipes(title='Tacos', quantity={}), author=current_user)
    recipes.append(Recipes(title='Ramen', quantity={}), author=current_user)
    recipes.append(Recipes(title='Chili', quantity={}), author=current_user)
    recipes.append(Recipes(title='Mac and Cheese', quantity={}), author=current_user)
    return recipes