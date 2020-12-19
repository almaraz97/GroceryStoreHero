from datetime import datetime
import json
import string
from flask import render_template, url_for, redirect, Blueprint, request, session
from GroceryHero.HarmonyTool import norm_stack, recipe_stack
from GroceryHero.Main.forms import ExtrasForm
from GroceryHero.Recipes.forms import Measurements, FullQuantityForm
from GroceryHero.Users.forms import FullHarmonyForm
from GroceryHero.models import Recipes, Aisles, Actions, User_Rec
from flask_login import current_user, login_required
from GroceryHero.Main.utils import (update_grocery_list, get_harmony_settings, get_history_stats,
                                    show_harmony_weights, apriori_test, convert_frac)
from GroceryHero.Pantry.utils import update_pantry
from GroceryHero import db

main = Blueprint('main', __name__)

"""
1. Added history, eaten, date joined, messages columns. Add history functionalities, add eaten functionalities, stats
visualisations, most eaten recipes, menu stats, better on mobile
2. fixed double reload of clear extras button, Allowed unsorted extras, Centered 'grocerylist' and buttons for mobile
views, added navbars for mobile, stopped saving redundant recipe weights
make mobile icons for advanced harmony form, fixed menu harmony display, fix recipe group weights,
Fix search bar in recipe page, Make cursor over cross off text, added harmony page better, validate numbers on quantity
Made ingredients alphabetical in menu list, but only from here on and when updating a recipe
add pantry functionality, add/remove shelf buttons like grocery-list buttons, download recipe single, fixed history,
bug when deleted, add "add all" for a recipe recommendation (ul ids instead of li), pantry column;add;remove;clear,
add similarity rating button for recipe recommendation, fixed pantry on anonymous user, added extras form validation,
add Measurement equivalence as part of object adding logic, Javascript adding from RHT recs, 
allowed fraction in form w validation, added fraction handling for various site utilities for recipe quantities, 
use of session in new and update recipe route handoffs, cython working, load recipe type in the update form
handle '2 1/2' in recipe scraper, show recipe type in recipe single
"""

# todo being able to download and upload recipes in json still necessary?
# todo prevent update on feed abuse


@main.route('/')
@main.route('/home')
def home():
    menu_list, groceries, username, harmony, overlap, aisles, most_eaten, least_eaten, statistics, borrowed = \
        [], [], [], 0, 0, None, None, None, None, None  # []*3, 0, 0, None*4
    if current_user.is_authenticated:
        menu_list = [recipe for recipe in Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()
                     if recipe.in_menu]
        borrowed = {x.recipe_id: x.eaten for x in User_Rec.query.filter_by(user_id=current_user.id, in_menu=True).all()}
        menu_list = menu_list + Recipes.query.filter(Recipes.id.in_(borrowed.keys())).all()
        aisles = {aisle.title: aisle.content.split(', ') for aisle in Aisles.query.filter_by(author=current_user)}
        groceries, overlap = current_user.grocery_list
        for aisle in groceries:  # Turns ingredients into Measurement object
            groceries[aisle] = [[item[0], Measurements(value=item[1], unit=item[2]), item[-1]]
                                for item in groceries[aisle]]
        aisles = None if len(aisles) < 1 else aisles  # If user has no aisles, set aisles to None
        menu_list = sorted(menu_list, key=lambda x: x.eaten)
        if len(menu_list) > 1:
            preferences = get_harmony_settings(current_user.harmony_preferences, holds=['max_sim', 'rec_limit', 'modifier'])
            recipes = {recipe.title: [x for x in recipe.quantity] for recipe in menu_list}
            modifier = 1 / (len(recipes) + 1) if current_user.harmony_preferences['modifier'] == 'Graded' else 1.0
            harmony = round((norm_stack(recipes, **preferences)**modifier*100), 2)
        username = current_user.username.capitalize()
        statistics = get_history_stats(current_user)
        if current_user.id == 9 and current_user.username == 'Andrea':
            return render_template('FOODSLIMEHOME.html', title='👏Home👏', menu_recipes=menu_list, groceries=groceries,
                                   sidebar=True, home=True, username=username, harmony_score=harmony, aisles=aisles,
                                   overlap=overlap, statistics=statistics)
    return render_template('home.html', title='Home', menu_recipes=menu_list, groceries=groceries,
                           sidebar=True, home=True, username=username, harmony_score=harmony, aisles=aisles,
                           overlap=overlap, statistics=statistics, borrowed=borrowed)


@main.route('/home/clear', methods=['GET', 'POST'])
def clear_menu():
    menu_recipes = Recipes.query.filter_by(author=current_user).filter_by(in_menu=True).all()  # Get all recipes
    borrowed_recipes = [x.recipe_id for x in User_Rec.query.filter_by(user_id=current_user.id, in_menu=True).all()]
    menu_recipes = menu_recipes + Recipes.query.filter(Recipes.id.in_(borrowed_recipes)).all()
    if len(menu_recipes) > 0:
        histories = current_user.history.copy()
        history = []
        for recipe in menu_recipes:
            if isinstance(recipe, Recipes):
                history.append(recipe.id)
            else:
                history.append(recipe.recipe_id)
            recipe.in_menu = False
            recipe.eaten = False
        update_pantry(current_user, menu_recipes)
        update_grocery_list(current_user)
        histories.append(history)
        current_user.history = histories
        recipes = Recipes.query.filter(Recipes.id.in_(history)).all()
        ids = [rec.id for rec in recipes]
        action = Actions(user_id=current_user.id, type_='Clear', recipe_ids=ids, date_created=datetime.utcnow(),
                         titles=[x.title for x in recipes])
        db.session.add(action)
        db.session.commit()
    return redirect(url_for('main.home'))


@main.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='Settings', sidebar=True, about=True)


@main.route('/harmony_tool', methods=['GET', 'POST'])
def harmony_tool():
    recommended = None
    if 'harmony' in session:  # todo use session to keep this information
        pass
    form = FullHarmonyForm()
    form.basic.groups.choices = range(2, 4)
    # Shows user their previous settings
    preferences = get_harmony_settings(current_user.harmony_preferences)
    preferences['rec_limit'] = 'No Limit'
    ing_weights, tastes, sticky = show_harmony_weights(current_user, preferences)
    if request.method == 'POST':  # Carry over preferences
        preferences['algorithm'] = form.advanced.algorithm.data
        preferences['modifier'] = form.advanced.modifier.data
        return redirect(url_for('main.harmony_tool2', preferences=preferences))
    return render_template('harmony.html', title='Harmony Tool', form=form,
                           ing_weights=ing_weights, tastes=tastes, sticky_weights=sticky, recommended=recommended,
                           sidebar=True, harmony=True)


# @main.route('/harmony_tool/<preferences>', methods=['GET', 'POST'])
# def harmony_tool2(preferences):
#     ing_weights, form, sticky, tastes, recommended = None, None, None, None, None
#     recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()
#     recipes = {r.title: r.quantity.keys() for r in recipe_list}
#     if preferences is not None:
#         preferences = {'advanced':
#                        {'pairs': None, 'pair_weight': None, 'ingredient': None, 'ingredient_weights': None,
#                         'ingredient_ex': None, 'ingredient_rem': None, 'ingredient2': None, 'sticky_weights': None,
#                         'history_exclude': None, 'recommend_num': None, 'algorithm': None, 'modifier': None
#                         }, 'basic': {'groups': None, 'excludes': None, 'similarity': None}}
#         form = FullHarmonyForm(data=preferences)
#     else:
#         return redirect(url_for('harmony_tool2'))
#     if request.method == 'POST':
#         recipe_history = [item for sublist in current_user.history[:int(form.advanced.history_exclude.data)]
#                           for item in sublist]
#         recipe_history = [x.title for x in Recipes.query.filter(Recipes.id.in_(recipe_history)).all()]
#         count = int(form.basic.groups.data)  # todo consider weighting settings
#         recommended, _ = recipe_stack(recipes, count, max_sim=form.basic.similarity.data,
#                                       excludes=form.basic.excludes.data + recipe_history,
#                                       limit=500_000, **preferences)
#     elif request.method == 'GET':
#         pass
#     return render_template('harmony.html', title='Harmony Tool', form=form, ing_weights=ing_weights, tastes=tastes,
#                            sticky_weights=sticky, recommended=recommended, sidebar=True, harmony=True)


@login_required
@main.route('/stats', methods=['GET', 'POST'])
def stats():  # Bar chart of recipe frequencies, ingredient frequencies, recipe UMAP
    history = current_user.history
    clears = len(history)
    if len(history) > 0:
        rules = apriori_test(current_user)
        # for rule in rules:
        #     print(rule)
        # listRules = [list(rules[i][0]) for i in range(0, len(rules))]
        # print(listRules)
        average_menu_len = sum([len(x) for x in history]) / len(history)
        all_ids = [r.id for r in Recipes.query.filter_by(author=current_user).all()]  # todo remove old ids?
        # Recipe History/Frequency
        history = [item for sublist in history for item in sublist if item in all_ids]  # Flatten ID list of lists
        history2 = current_user.history
        history_set = set(history)
        history_count = {}
        for item in history_set:
            history_count[item] = history.count(item)
        history_count = sorted(history_count.items(), key=lambda x: x[1], reverse=True)
        history_count_names = [list(x) for x in
                               {Recipes.query.filter_by(id=k).first().title: v for k, v in history_count}.items()]
        history_count_names = [x + [round(x[1] / len(history2), 4)] for x in
                               history_count_names]
        # Ingredient History/Frequency
        ingredient_history = [[x for x in Recipes.query.filter_by(id=k).first().quantity.keys()] * v for
                              k, v in history_count]
        ingredient_history = [item for sublist in ingredient_history for item in sublist]
        ingredient_set = set(ingredient_history)
        ingredient_count = {}
        for item in ingredient_set:
            ingredient_count[item] = ingredient_history.count(item)
        ingredient_count = sorted(ingredient_count.items(), key=lambda x: x[1], reverse=True)
        ingredient_count = [list(x) + [round(x[1] / len(history2), 4)] for x in ingredient_count]
        # Total Harmony
        all_recipes = Recipes.query.filter_by(author=current_user).all()
        harmony = round((norm_stack({r.title: r.quantity.keys() for r in all_recipes}) * 100), 5)
        avg_harmony = []
        for batch in history2:
            if len(batch) > 1:
                recs = {recipe.title: recipe.quantity for recipe in Recipes.query.filter(Recipes.id.in_(batch)).all()}
                modifier = 1 / (len(recs) + 1) if current_user.harmony_preferences['modifier'] == 'Graded' else 1.0
                h = (norm_stack(recs) ** modifier) * 100
                avg_harmony.append(h)
        avg_harmony = round(sum(avg_harmony) / len(avg_harmony), 5)
    else:
        history_count_names, ingredient_history, ingredient_count, \
        harmony, avg_harmony, average_menu_len, rules = None, None, None, 0, 0, 0, None
    return render_template('stats.html', title='Your Statistics', sidebar=True, about=True,
                           recipe_history=history_count_names, ingredient_count=ingredient_count, harmony=harmony,
                           avg_harmony=avg_harmony, average_menu_len=average_menu_len, frequency_pairs=rules,
                           clears=clears)


@main.route('/extras', methods=['GET', 'POST'])
def add_to_extras():
    aisles = Aisles.query.filter_by(user_id=current_user.id).all()
    ingredients = [aisle.content.split(', ') for aisle in aisles]
    choices = sorted(set([item for sublist in ingredients for item in sublist if item]))
    form = ExtrasForm()
    form.multi.choices = [('', 'Ingredients Choices')] + [(choice, choice) for choice in choices]
    if form.validate_on_submit():  # Form is submitted and not empty list
        form.other.data.split(', ')
        choices = form.multi.data
        if form.other.data != '':
            choices = choices + [string.capwords(x.strip()) for x in form.other.data.split(', ') if x.strip() != '']
        if choices == '':  # No selection  # todo add this to
            return redirect(url_for('main.add_to_extras'))
        # if '' in choices:  # Default and maybe selections
        #     choices.remove('')  # Remove default
        #     if not choices:  # if the selection only included the empty value
        #         return redirect(url_for('main.add_to_extras'))  # Reload page
        choices = json.dumps(choices)
        return redirect(url_for('main.add_extras', ingredients=choices))
    return render_template('add_extras.html', legend='Add Extras', form=form, ingredients=True)


@main.route('/extras_add/<ingredients>', methods=['GET', 'POST'])
def add_extras(ingredients):
    ingredients = json.loads(ingredients)
    data = {'ingredient_forms': [{f'ingredient_quantity': 1.0, f'ingredient_type': 'Unit'}
                                 for _ in ingredients]}
    form = FullQuantityForm(data=data)  # List of dictionaries
    form.ingredients = ingredients
    if form.validate_on_submit():
        # user.grocery_list [{'Another Name': [['Bread Crumbs', 1, 'Unit', 0], ...], 'Alex': []}, overlap[int]]
        # Extras list Format: [ [AisleName, [IngredientName, quantity, unit, BoolCheck]],...]
        entries, unsorted = [], []
        aisles = Aisles.query.filter_by(user_id=current_user.id).all()
        for i, ingredient_form in enumerate(form.ingredient_forms):  # For item in user entered extras
            for j, aisle in enumerate(aisles):  # For aisle in user aisles
                if form.ingredients[i] in aisle.content.split(', ') and j <= len(aisles):  # If ingredient in that aisle
                    entries.append([aisle.title, [form.ingredients[i],
                                                  convert_frac(ingredient_form.ingredient_quantity.data),
                                                  ingredient_form.ingredient_type.data, 0]])  # Add to extras
                    break
                else:  # All aisles have been searched, no matches
                    unsorted.append([form.ingredients[i],  # todo verify this works
                                     convert_frac(ingredient_form.ingredient_quantity.data),
                                     ingredient_form.ingredient_type.data, 0])
        for item in unsorted:
            entries.append(['Other (unsorted)', item])  # Add to extras
        e_copy = current_user.extras.copy()
        for item in entries:  # Add new extras to old extras column
            e_copy.append(item)
            current_user.extras = e_copy
        update_grocery_list(current_user)
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('add_extras.html', legend='Add Their Units', form=form, add=True)


@main.route('/home/change_grocerylist', methods=['POST'])
def change_to_grocerylist():
    item_id = request.form['item_id'].split(', ')
    strike = int(request.form['strike'])
    temp, overlap = current_user.grocery_list.copy()
    for aisle in temp:
        for i, item in enumerate(temp[aisle]):
            if [item[0], item[2]] == item_id:
                temp[aisle][i] = [item[0], item[1], item[2], strike]
    current_user.grocery_list = []
    db.session.commit()
    current_user.grocery_list = [temp, overlap]
    db.session.commit()
    return json.dumps({'result': 'success'})


@main.route('/home/change_eaten', methods=['POST'])  # todo might affect friends list menu stuff
def change_to_eaten():
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.filter_by(id=recipe_id).first()
    if recipe.author != current_user:
        recipe = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    recipe.eaten = not recipe.eaten
    db.session.commit()
    return json.dumps({'result': 'success'})


@main.route('/extras_clear', methods=['GET', 'POST'])
def clear_extras():
    current_user.extras = []
    update_grocery_list(current_user)
    db.session.commit()
    return redirect(url_for('main.home'))

    # data = {'aisle_forms': [{'content': [(item, item) for item in aisle.content.split(', ')]} for aisle in aisles]}
    # form = AddExtrasForm(data=data)
    # form = ExtrasForm()
    # form.content.choices = [(x, x) for x in sorted(aisles.content.split(', '))]
    # form = []
    # for aisle in aisles:
    #     entry = ExtrasForm()
    #     entry.content.choices = [('', 'Select Options (ctrl+click)')] + \
    #                             [(x, x) for x in sorted(aisle.content.split(', '))]
    #     form.append([aisle.title, entry])
    # entry.content.choices = [(x, x) for x in sorted(aisle.content.split(', '))]
    # print(entry.content.choices)
    # form.aisle_forms.append_entry(entry)
    # form.aisle_forms.entries
    # print(form.aisle_forms.entries)
    # for entry in form.aisle_forms:
    #     print(entry)
    #     aisle = [aisle for aisle in aisles if aisle.title == entry.name]
    #     print(aisle)
    #     entry.content.choices = aisle.contents.split(', ')
    #     print()
    # print(form.data)
    # print(form.aisle_forms.data)
