from GroceryHero.HarmonyTool import norm_stack
from GroceryHero.Main.forms import ExtrasForm
from GroceryHero.Recipes.forms import FullQuantityForm
from GroceryHero.Recipes.utils import Measurements
from GroceryHero.Users.forms import FullHarmonyForm
from GroceryHero.models import Recipes, Aisles, Actions, User_Rec
from GroceryHero.Main.utils import (update_grocery_list, get_harmony_settings, get_history_stats,
                                    show_harmony_weights, convert_frac, stats_graph, change_extras)
from GroceryHero.Pantry.utils import update_pantry
from GroceryHero import db
from flask import render_template, url_for, redirect, Blueprint, request, session
from flask_login import current_user, login_required
from datetime import datetime
from glob import glob
import json
import string

main = Blueprint('main', __name__)


@main.route('/', methods=['GET', 'POST'])
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':  # todo send me an email
        pass
    return render_template('landing.html')


@login_required
@main.route('/home')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('users.auth_login'))
    menu_list, groceries, username, harmony, overlap, aisles, most_eaten, least_eaten, statistics, borrowed = \
        [], [], [], 0, 0, None, None, None, None, None  # []*3, 0, 0, None*4
    menu_list = [recipe for recipe in Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()
                 if recipe.in_menu]
    borrowed = {x.recipe_id: x.eaten for x in User_Rec.query.filter_by(user_id=current_user.id, in_menu=True).all()}
    menu_list = menu_list + Recipes.query.filter(Recipes.id.in_(borrowed.keys())).all()
    aisles = {(aisle.order, aisle.title): aisle.content.split(', ')
              for aisle in Aisles.query.filter_by(author=current_user)}

    aisles_order_dict = {i: name for i, (_, name) in enumerate(sorted(aisles.keys(), key=lambda x: x[0]))}
    if aisles_order_dict:
        aisles_order_dict[max(aisles_order_dict.keys()) + 1] = 'Other (unsorted)'  # Todo make this global variable
    else:
        aisles_order_dict[0] = 'Other (unsorted)'
    groceries, overlap = current_user.grocery_list if len(current_user.grocery_list) > 1 else [{}, 0]

    for aisle in groceries:  # Ingredient to Measurement object  # Must be in db because of strike variable
        groceries[aisle] = [[item[0], Measurements(value=item[1], unit=item[2]), item[-1]]
                            for item in groceries[aisle]]  # Change to dictionary {'ingredient':M, 'strike':0,...}

    menu_list = sorted(menu_list, key=lambda x: x.eaten)
    if len(menu_list) > 1:
        preferences = get_harmony_settings(current_user.harmony_preferences, holds=['max_sim', 'rec_limit', 'modifier'])
        recipes = {recipe.title: [x for x in recipe.quantity] for recipe in menu_list}
        modifier = 1 / (len(recipes) + 1) if current_user.harmony_preferences['modifier'] == 'Graded' else 1.0
        harmony = round((norm_stack(recipes, **preferences) ** modifier * 100), 2)
    username = current_user.username.capitalize()
    statistics = get_history_stats(current_user)
    return render_template('home.html', title='Home', menu_recipes=menu_list, groceries=groceries,
                           sidebar=True, home=True, username=username, harmony_score=harmony, aisles=len(aisles),
                           overlap=overlap, statistics=statistics, borrowed=borrowed, order_dict=aisles_order_dict)


@login_required
@main.route('/home/clear', methods=['GET', 'POST'])
def clear_menu():
    menu_recipes = Recipes.query.filter_by(author=current_user, in_menu=True, eaten=True).all()  # Only eaten ones
    borrowed_recipes = User_Rec.query.filter_by(user_id=current_user.id, in_menu=True, eaten=True).all()
    menu_recipes = menu_recipes + borrowed_recipes
    if len(menu_recipes) > 0:
        histories = current_user.history.copy()
        history = []
        for recipe in menu_recipes:
            if isinstance(recipe, Recipes):
                history.append(recipe.id)
            elif isinstance(recipe, User_Rec):
                history.append(recipe.recipe_id)
            recipe.in_menu = False
            recipe.eaten = False
            recipe.times_eaten = recipe.times_eaten + 1
        update_pantry(current_user, menu_recipes)
        update_grocery_list(current_user)
        histories[datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')] = history
        current_user.history = histories
        recipes = Recipes.query.filter(Recipes.id.in_(history)).all()
        ids = [rec.id for rec in recipes]
        titles = [x.title for x in recipes]
        if titles:
            action = Actions(user_id=current_user.id, type_='Clear', recipe_ids=ids, date_created=datetime.utcnow(),
                             titles=titles)
            db.session.add(action)
        db.session.commit()
    return redirect(url_for('main.home'))


@main.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='Settings', sidebar=True, about=True)


@login_required
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
@main.route('/stats', methods=['GET', 'POST'])  # todo include borrowed recipes
def stats():  # Bar chart of recipe frequencies, ingredient frequencies, recipe UMAP
    history_count_names, ingredient_history, ingredient_count, harmony, avg_harmony, average_menu_len, rules, timeline,\
        all_recipes, graph, timeline = None, None, None, 0, 0, 0, None, {}, None, '', {}
    history = current_user.history
    clears = len(history)
    if len(history) > 0:
        # rules = apriori_test(current_user)
        # listRules = [list(rules[i][0]) for i in range(0, len(rules))]
        timeline = sorted([[datetime.strptime(date, '%Y-%m-%d %H:%M:%S'),
                            [r.title for r in Recipes.query.filter(Recipes.id.in_(rec_list)).all()]]
                           for date, rec_list in history.items()], key=lambda x: x[0], reverse=True)
        average_menu_len = sum([len(x) for x in history.values()]) / len(history)
        all_ids = [r.id for r in current_user.recipes]
        # Recipe History/Frequency
        history = [item for sublist in history.values() for item in sublist if item in all_ids]
        history2 = current_user.history.values()
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
            recs = {recipe.title: recipe.quantity for recipe in Recipes.query.filter(Recipes.id.in_(batch)).all()}
            if len(recs) > 1:
                modifier = 1 / (len(recs) + 1) if current_user.harmony_preferences['modifier'] == 'Graded' else 1.0
                h = (norm_stack(recs) ** modifier) * 100
                avg_harmony.append(h)
        avg_harmony = round(sum(avg_harmony) / len(avg_harmony), 5)
    if len(current_user.recipes) > 1:
        time_format = '%Y-%m-%d'
        now = datetime.now()
        now_str = now.strftime(time_format)
        user_graphs = glob(f'GroceryHero/static/visualizations/{current_user.id}*')
        last_graph = user_graphs[-1].split('_')[-1][:-4]  # Remove path and jpeg, leaving datetime
        last_graph = datetime.strptime(last_graph, time_format) if user_graphs else None
        if (last_graph is None) or ((now-last_graph).days >= 7):
            stats_graph(current_user, all_recipes, now=now_str)
            graph = url_for('static', filename=f'visualizations/{current_user.id}_{now_str}.jpg')
        else:
            graph = url_for('static', filename=f'visualizations/{current_user.id}_{last_graph.strftime(time_format)}.jpg')
    return render_template('stats.html', title='Your Statistics', sidebar=True, about=True, clears=clears, graph=graph,
                           recipe_history=history_count_names, ingredient_count=ingredient_count, harmony=harmony,
                           avg_harmony=avg_harmony, average_menu_len=average_menu_len, frequency_pairs=rules,
                           timeline=timeline)


@login_required
@main.route('/extras', methods=['GET', 'POST'])
def add_to_extras():  # Get ingredient names in form
    aisles = Aisles.query.filter_by(user_id=current_user.id).all()
    ingredients = [aisle.content.split(', ') for aisle in aisles]
    choices = sorted({item for sublist in ingredients for item in sublist if item})
    form = ExtrasForm()
    form.multi.choices = [('', 'Ingredients Choices')] + [(choice, choice) for choice in choices]
    if form.validate_on_submit():  # Form is submitted and not empty list
        choices = form.multi.data
        if form.other.data != '':
            choices = choices + [string.capwords(x.strip()) for x in form.other.data.split(', ') if x.strip() != '']
        if choices == '':  # No selection  # todo add this to form?
            return redirect(url_for('main.add_to_extras'))
        # if '' in choices:  # Default and maybe selections
        #     choices.remove('')  # Remove default
        #     if not choices:  # if the selection only included the empty value
        #         return redirect(url_for('main.add_to_extras'))  # Reload page
        choices = json.dumps(choices)
        return redirect(url_for('main.add_extras', ingredients=choices))
    return render_template('add_extras.html', legend='Add Extras', form=form, ingredients=True)


@login_required
@main.route('/extras_add/<ingredients>', methods=['GET', 'POST'])
def add_extras(ingredients):  # Add ingredient units/values
    ingredients = json.loads(ingredients)
    data = {'ingredient_forms': [{f'ingredient_quantity': 1.0, f'ingredient_type': 'Unit'}
                                 for _ in ingredients]}
    form = FullQuantityForm(data=data)  # List of dictionaries
    form.ingredients = ingredients
    if form.validate_on_submit():
        # user.grocery_list [{'Another Name': [['Bread Crumbs', 1, 'Unit', 0], ...], 'Alex': []}, int(overlap)]
        # Extras list Format: [ [AisleName, [IngredientName, quantity, unit, BoolCheck]],...]
        added_extras = []
        for i, ingredient_form in enumerate(form.ingredient_forms):
            ing_name = form.ingredients[i]
            value = convert_frac(ingredient_form.ingredient_quantity.data)
            unit = ingredient_form.ingredient_type.data
            added_extras.append([ing_name, value, unit, 0])

        old_extras = current_user.extras.copy()
        grocery_list = current_user.grocery_list.copy()
        aisles = current_user.aisles
        new_extras, new_grocery_list = change_extras(old_extras, added_extras,
                                                     grocery_list, aisles, remove=False)
        current_user.extras, current_user.grocery_list = [], []
        db.session.commit()
        current_user.extras = new_extras
        current_user.grocery_list = new_grocery_list
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('add_extras.html', legend='Add Their Units', form=form, add=True)


@login_required
@main.route('/extras_clear', methods=['POST'])
def clear_extras():
    old_extras = current_user.extras.copy()
    grocery_list = current_user.grocery_list.copy()
    aisles = current_user.aisles

    _, new_grocery_list = change_extras(old_extras, old_extras, grocery_list, aisles, remove=True)
    current_user.extras, current_user.grocery_list = [], []
    db.session.commit()
    current_user.grocery_list = new_grocery_list
    db.session.commit()
    return redirect(url_for('main.home'))


# @login_required
# @main.route('/remove_extra', methods=['POST'])
# def remove_extra():
#     # old_extras = current_user.extras.copy()
#     # grocery_list = current_user.grocery_list.copy()
#     #
#     # new_extras, new_grocery_list = change_extras(old_extras, [], grocery_list, remove=True)
#     # current_user.extras, current_user.grocery_list = [], []
#     # db.session.commit()
#     # current_user.grocery_list = new_grocery_list
#     # db.session.commit()
#     return redirect(url_for('main.home'))


@login_required
@main.route('/home/change_grocerylist', methods=['POST'])
def change_to_grocerylist():  # Change strike
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


@login_required
@main.route('/home/change_eaten', methods=['POST'])
def change_to_eaten():
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.filter_by(id=recipe_id).first()
    if recipe.author != current_user:
        recipe = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    recipe.eaten = not recipe.eaten
    db.session.commit()
    return json.dumps({'result': 'success'})

