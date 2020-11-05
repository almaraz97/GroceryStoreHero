from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from GroceryHero.Pantry.forms import PantryBarForm, QuantityForm, FullQuantityForm, ShelfForm
from GroceryHero.HarmonyTool import recipe_stack
from GroceryHero.models import Recipes
from GroceryHero import db
import string
import json

pantry = Blueprint('pantry', __name__)


@pantry.route('/pantry', methods=['GET', 'POST'])
def pantry_page():
    form = PantryBarForm()
    if not current_user.is_authenticated:
        return redirect(url_for('main.home'))
    else:
        # categories = current_user.pantry.keys()
        temp = [recipe.quantity.keys() for recipe in Recipes.query.filter_by(author=current_user)]
        form.content.choices = [(x, x) for x in sorted(set(item for sublist in temp for item in sublist))]
        if form.validate_on_submit():
            print("Validated")
    return render_template('pantry.html', title='Pantry', sidebar=True, pantry=True, form=form)


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
    data = {'ingredient_forms': [{'ingredient_quantity': send['quantity'][ingredient][0],
                                  'ingredient_type': send['quantity'][ingredient][1]}
                                 for ingredient in send['quantity'].keys()]}
    form = FullQuantityForm(data=data)
    form.ingredients = [x for x in send['quantity'].keys()]
    if form.is_submitted():
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [Q, M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}
        # recipe = Recipes(title=(recipe['title']).capitalize(), quantity=formatted, author=current_user,
        #                  notes=recipe['notes'])
        # db.session.add(recipe)
        # db.session.commit()
        flash('Your shelf has been created!', 'success')
        return redirect(url_for('pantry.pantry_page'))
    return render_template('new_shelf_quantity.html', title='New Shelf', form=form, legend='Ingredient Quantities',
                           recipe=send)


def new_recipe_quantity(recipe):
    recipe = json.loads(recipe)  # Has {RecipeName: string, Quantity: {ingredient: [value,type]}}
    data = {'ingredient_forms': [{'ingredient_quantity': recipe['quantity'][ingredient][0],
                                  'ingredient_type': recipe['quantity'][ingredient][1]}
                                 for ingredient in recipe['quantity'].keys()]}
    form = FullQuantityForm(data=data)
    form.ingredients = [x for x in recipe['quantity'].keys()]
    if form.is_submitted():
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [Q, M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}
        recipe = Recipes(title=(recipe['title']).capitalize(), quantity=formatted, author=current_user,
                         notes=recipe['notes'])
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('recipes.recipes_page'))
    return render_template('recipe_quantity.html', title='New Recipe', form=form, legend='Recipe Quantities',
                           recipe=recipe)

