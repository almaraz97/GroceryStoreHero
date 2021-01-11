from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required

from GroceryHero.Main.forms import ExtrasForm
from GroceryHero.Main.utils import convert_frac
from GroceryHero.Pantry.utils import add_pantry
from GroceryHero.Pantry.forms import PantryBarForm, FullQuantityForm, ShelfForm, DeleteShelfForm, AddToShelfForm
from GroceryHero.Recipes.utils import Measurements
from GroceryHero.models import Recipes
from GroceryHero import db
import string
import json

pantry = Blueprint('pantry', __name__)


@pantry.route('/pantry', methods=['GET', 'POST'])
def pantry_page():
    form = PantryBarForm()
    if current_user.is_authenticated:
        if current_user.pantry is None:
            current_user.pantry = {}
            db.session.commit()
        # # {Shelf: {Ingredient: [quantity, unit],...},...}
        all_pantry = current_user.pantry
        for shelf in all_pantry:
            all_pantry[shelf] = {k: all_pantry[shelf][k] for k in sorted(all_pantry[shelf])}
        all_pantry = {name: {ing: Measurements(value=int(L[0]) if float(L[0]).is_integer() else L[0], unit=L[1])
                             for ing, L in all_pantry[name].items()}
                      for name, ing in all_pantry.items()}
        # Sidebar adding choices
        ingredients = [recipe.quantity.keys() for recipe in Recipes.query.filter_by(author=current_user)]  # Ingredients
        ingredients = ingredients + [current_user.pantry[item] for item in [key for key in current_user.pantry]]
        form.content.choices = [(x, x) for x in sorted(set(item for sublist in ingredients for item in sublist))]
        form.name.choices = [(x, x) for x in all_pantry.keys()]
        if form.validate_on_submit():
            shelf = form.name.data
            ingredients = {ing: [form.ingredient_quantity.data, form.ingredient_type.data] for ing in form.content.data}
            add_pantry(current_user, ingredients, shelf, form.add.data)
            all_pantry = current_user.pantry
            all_pantry = {name: {ing: Measurements(value=int(L[0]) if float(L[0]).is_integer() else L[0], unit=L[1])
                                 for ing, L in all_pantry[name].items()}
                          for name, ing in all_pantry.items()}
    else:
        all_pantry = []
        form.content.choices = [('No Ingredients Yet', 'No Ingredients Yet')]
    return render_template('pantry.html', title='Pantry', sidebar=True, pantry=True, form=form, shelves=all_pantry)


@login_required
@pantry.route('/new_shelf', methods=['GET', 'POST'])
def new_shelf():
    form = ShelfForm()
    if not current_user.is_authenticated:
        return redirect(url_for('main.home'))
    else:
        if form.validate_on_submit():  # Send data to quantity page
            ingredients = sorted([string.capwords(x.strip()) for x in form.content.data.split(',') if x.strip() != ''])
            quantity = {ingredient: [1, 'Unit'] for ingredient in ingredients}
            send = json.dumps({'name': form.name.data, 'quantity': quantity})
            return redirect(url_for('pantry.new_shelf_quantity', send=send))
    return render_template('new_shelf.html', title='Pantry', legend='New Shelf', form=form)


@pantry.route('/new_shelf/<string:send>', methods=['GET', 'POST'])
@login_required
def new_shelf_quantity(send):
    send = json.loads(send)  # Has {RecipeName: string, Quantity: {ingredient: [value,type]}}
    shelf_name = string.capwords(send['name'].strip())
    data = {'ingredient_forms': [{'ingredient_quantity': send['quantity'][ingredient][0],
                                  'ingredient_type': send['quantity'][ingredient][1]}
                                 for ingredient in send['quantity'].keys()]}
    form = FullQuantityForm(data=data)
    form.ingredients = [x for x in send['quantity'].keys()]
    if form.is_submitted():  # change to validate
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [int(Q), M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}
        copy = current_user.pantry.copy()
        copy[shelf_name] = formatted
        current_user.pantry = copy
        db.session.commit()
        flash('Your shelf has been created!', 'success')
        return redirect(url_for('pantry.pantry_page'))
    return render_template('new_shelf_quantity.html', title='New Shelf', form=form, legend='Ingredient Quantities',
                           recipe=send)


@pantry.route('/delete_shelf', methods=['GET', 'POST'])
def delete_shelf():
    shelves = current_user.pantry.copy()
    if len(shelves) < 1:
        return redirect(url_for('pantry.pantry_page'))
    form = DeleteShelfForm()
    form.shelves.choices = [(x, x) for x in shelves]
    if form.validate_on_submit():
        deletes = form.shelves.data
        for delete in deletes:
            del shelves[delete]
        current_user.pantry = {}  # todo ?double needed
        db.session.commit()
        current_user.pantry = shelves
        db.session.commit()
        return redirect(url_for('pantry.pantry_page'))
    return render_template('delete_shelf.html', title='Pantry', legend='Delete Shelves', form=form)


@pantry.route('/add_to_shelf', methods=['GET', 'POST'])
def add_to_shelf():
    form = AddToShelfForm()
    shelves = current_user.pantry.copy()
    if len(shelves) < 1:
        return redirect(url_for('pantry.pantry_page'))
    ingredients = [list(x.quantity.keys()) for x in Recipes.query.filter_by(author=current_user).all()]
    shelf_ings = [list(shelves[shelf].keys()) for shelf in shelves]
    ingredients = sorted(set([item for sublist in ingredients+shelf_ings for item in sublist]))
    form.multi.choices = [('', 'Ingredients Choices')] + [(choice, choice) for choice in ingredients]
    form.shelves.choices = [('', 'Shelf Choices')] + [(x, x) for x in shelves.keys()]
    if form.validate_on_submit():  # Form is submitted and not empty list
        form.other.data.split(', ')
        choices = form.multi.data
        if form.other.data != '':
            choices = choices + [string.capwords(x.strip()) for x in form.other.data.split(', ') if x.strip() != '']
        if choices == '':  # No selection  # todo add this to
            return redirect(url_for('main.add_to_extras'))
        choices = json.dumps(choices)
        return redirect(url_for('pantry.shelf_add', ingredients=choices))
    return render_template('add_extras.html', legend='Add To Shelves', form=form, ingredients=True, shelves=True)


@pantry.route('/shelf_add/<ingredients>', methods=['GET', 'POST'])
def shelf_add(ingredients):
    ingredients = json.loads(ingredients)
    data = {'ingredient_forms': [{f'ingredient_quantity': 1.0, f'ingredient_type': 'Unit'}
                                 for _ in ingredients]}
    form = FullQuantityForm(data=data)  # List of dictionaries
    form.ingredients = ingredients
    shelves = current_user.pantry
    # print(form.validate())
    if form.validate_on_submit():
        # print("Bye")
        # user.grocery_list [{'Another Name': [['Bread Crumbs', 1, 'Unit', 0], ...], 'Alex': []}, overlap[int]]
        # Extras list Format: [ [AisleName, [IngredientName, quantity, unit, BoolCheck]],...]
        entries = []
        for i, ingredient_form in enumerate(form.ingredient_forms):  # For item in user entered extras
            for j, shelf in enumerate(shelves):  # For aisle in user aisles
                if form.ingredients[i] in shelves[shelf].keys() and j <= len(shelves):  # If ingredient in that aisle
                    entries.append([shelf, [form.ingredients[i],
                                            convert_frac(ingredient_form.ingredient_quantity.data),
                                            ingredient_form.ingredient_type.data, 0]])  # Add to extras
                    break
        # print(entries)
        # db.session.commit()
        return redirect(url_for('pantry.pantry_page'))
    return render_template('add_extras.html', legend='Add Their Units', form=form, add=True)
