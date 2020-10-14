import json
import string
from flask import render_template, url_for, redirect, Blueprint, request, abort, flash
from GroceryHero.HarmonyTool import norm_stack
from GroceryHero.Main.forms import ExtrasForm
from GroceryHero.Recipes.forms import Measurements, FullQuantityForm
from GroceryHero.Users.forms import HarmonyForm, AdvancedHarmonyForm, FullHarmonyForm
from GroceryHero.Users.utils import load_harmony_form, update_harmony_preferences
from GroceryHero.models import Recipes, Aisles, User
from flask_login import current_user, login_required
from GroceryHero.Main.utils import update_grocery_list, ensure_harmony_keys, get_harmony_settings, get_history_stats
from GroceryHero import db

main = Blueprint('main', __name__)


# Now
# Added history, eaten, date joined, messages columns. Add history functionalities, add eaten functionalities, stats
# visualisations, most eaten recipes, menu stats, better on mobile

# fixed double reload of clear extras button, Allowed unsorted extras, Centered 'grocerylist' and buttons for mobile
# views, added navbars for mobile, stopped saving redundant recipe weights
# todo change to form.validate_on_submit() and add hidden tags # todo Allow fractions for quantity page
# todo add average menu size to stats
# todo add store title to grocery-list above aisle names
# todo Allow each store to have aisles 1-10
# todo add all harmony keys to check_columns, default model, and other places
# todo fix password reset abilities (being sent another link that will work)
# Soon
# todo Fix search bar in recipe page
# todo figure our JSON situation from harmony preferences JSON column coming in and out
# todo save the day a history clear was performed (can find average time before eating recipe again)
# todo Make cursor over cross off text, (cursor: pointer;) in CSS class for LI
# todo make mobile icons for advanced harmony form
# todo Javascript adding from RHT recommended
# Later
# todo have aisle ingredients show recipes that have that ingredient
# todo Store RHT dict of combos (value as HS), exclude, wont be recalculated (subsets could be excluded and average HS?)
# todo Add picture functionality
# todo Add friend list to see their recipes in explore page
# todo Add ability to make recipe public + filthy filter


@main.route('/')
@main.route('/home')
def home():
    menu_list, groceries, username, harmony_score, overlap, aisles, most_eaten, least_eaten = \
        [], [], [], 0, 0, None, None, None
    if current_user.is_authenticated:
        ensure_harmony_keys(current_user)  # Make sure groceryList, extras and harmony_preferences JSON columns exist
        preferences = get_harmony_settings(current_user.harmony_preferences)  # Harmony preferences dict
        menu_list = [recipe for recipe in Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()
                     if recipe.in_menu]
        # GroceryList maker
        aisles = {aisle.title: aisle.content.split(', ') for aisle in Aisles.query.filter_by(author=current_user)}
        groceries, overlap = current_user.grocery_list
        for aisle in groceries:  # Turns ingredients into Measurement object
            groceries[aisle] = [[item[0], Measurements(value=item[1], unit=item[2]), item[-1]]
                                for item in groceries[aisle]]
        aisles = None if len(aisles) < 1 else aisles  # If user has no aisles, set aisles to None
        if len(menu_list) > 1:
            harmony_score = round((norm_stack({recipe.title: recipe.quantity for recipe in menu_list}, **preferences))
                                  ** (1 / (len(menu_list) * 2 - 3)) * 100, 1)
        username = current_user.username.capitalize()
        most_eaten, least_eaten = get_history_stats(current_user)
    return render_template('home.html', title='Home', menu_recipes=menu_list, groceries=groceries,
                           sidebar=True, home=True, username=username, harmony_score=harmony_score, aisles=aisles,
                           overlap=overlap, most_eaten=most_eaten, least_eaten=least_eaten)


@main.route('/home/clear', methods=['GET', 'POST'])
def clear_menu():
    menu_recipes = Recipes.query.filter_by(author=current_user).filter_by(in_menu=True).all()  # Get all recipes
    if len(menu_recipes) > 0:
        histories = current_user.history.copy()
        history = []
        for recipe in menu_recipes:
            history.append(recipe.id)
            recipe.in_menu = False
            recipe.eaten = False
        update_grocery_list(current_user)  # Update grocery list
        histories.append(history)
        current_user.history = histories
        db.session.commit()
    else:
        pass
    return redirect(url_for('main.home'))


@main.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='Settings', sidebar=True, about=True)


@main.route('/harmony_tool', methods=['GET', 'POST'])
def harmony_tool():
    form = FullHarmonyForm()
    form1 = HarmonyForm()
    form2 = load_harmony_form(AdvancedHarmonyForm(), current_user)
    # Shows user their previous settings
    preferences = get_harmony_settings(current_user.harmony_preferences)
    ing_weights = preferences['ingredient_weights']
    ing_weights = json.loads(ing_weights) if isinstance(ing_weights, str) else ing_weights
    ing_weights = ', '.join([str(key) + ': ' + str(value) for key, value in ing_weights.items()])
    tastes = preferences['tastes']
    tastes = json.loads(tastes) if isinstance(tastes, str) else tastes  # Formatting for showing pairs to user
    tastes = '\n'.join([str(key[0])+', '+str(key[1])+': '+str(value) for key, value in tastes.items()])
    sticky = preferences['sticky_weights']
    sticky = json.loads(sticky) if isinstance(sticky, str) else sticky
    sticky = ', '.join([str(key) + ': ' + str(value) for key, value in sticky.items()])
    if form2.is_submitted():
        update_harmony_preferences(form2, current_user)
        db.session.commit()
        # flash('Your settings have been updated', 'success')
        return redirect(url_for('main.harmony_tool'))
    return render_template('harmony.html', title='Harmony', form1=form1, form2=form2, form=form,
                           ing_weights=ing_weights, tastes=tastes, sticky_weights=sticky)


@login_required
@main.route('/stats', methods=['GET', 'POST'])
def stats():  # Bar chart of recipe frequencies, ingredient frequencies, recipe UMAP
    history = current_user.history
    if len(history) > 0:
        # Recipe History/Frequency
        history = [item for sublist in history for item in sublist]
        history2 = current_user.history
        history_set = set(history)
        history_count = {}
        for item in history_set:
            history_count[item] = history.count(item)
        history_count = sorted(history_count.items(), key=lambda x: x[1], reverse=True)
        history_count_names = [list(x) for x in {Recipes.query.filter_by(id=k).first().title: v for k, v in history_count}.items()]
        history_count_names = [x+[round(x[1]/len(history2), 4)] for x in
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
        ingredient_count = [list(x)+[round(x[1]/len(history2), 4)] for x in ingredient_count]
        # Total Harmony
        all_recipes = Recipes.query.filter_by(author=current_user).all()
        harmony = round((norm_stack({r.title: r.quantity.keys() for r in all_recipes}) * 100), 5)
        avg_harmony = []
        for batch in history2:
            if len(batch) > 1:
                h = (norm_stack({recipe.title: recipe.quantity for recipe in
                                Recipes.query.filter(Recipes.id.in_(batch)).all()})**(1/(len(batch)*2-3)))*100
                avg_harmony.append(h)
        avg_harmony = round(sum(avg_harmony)/len(avg_harmony), 5)
    else:
        history_count_names, ingredient_history, ingredient_count, harmony, avg_harmony = None, None, None, None, None
    return render_template('stats.html', title='Your Statistics', sidebar=True, about=True,
                           recipe_history=history_count_names, ingredient_count=ingredient_count, harmony=harmony,
                           avg_harmony=avg_harmony)


@main.route('/extras', methods=['GET', 'POST'])
def add_to_extras():
    aisles = Aisles.query.filter_by(user_id=current_user.id).all()
    ingredients = [aisle.content.split(', ') for aisle in aisles]
    choices = sorted(set([item for sublist in ingredients for item in sublist if item]))
    form = ExtrasForm()
    form.content.choices = [('', 'Ingredients Choices')] + [(choice, choice) for choice in choices]
    if form.is_submitted():  # Form is submitted and not empty list
        form.other.data.split(', ')
        choices = form.content.data+[string.capwords(x.strip()) for x in form.other.data.split(', ') if x.strip() != '']
        if choices == '':  # No selection
            return redirect(url_for('main.add_to_extras'))
        if '' in choices:  # Default and maybe selections
            choices.remove('')  # Remove default
            if not choices:  # if the selection only included the empty value
                return redirect(url_for('main.add_to_extras'))  # Reload page
        choices = json.dumps(choices)
        return redirect(url_for('main.add_extras', ingredients=choices))
    return render_template('add_extras.html', legend='Add Extras From Aisles', form=form, ingredients=True)


@main.route('/extras_add/<ingredients>', methods=['GET', 'POST'])
def add_extras(ingredients):
    ingredients = json.loads(ingredients)
    data = {'ingredient_forms': [{'ingredient_quantity': 1.0, 'ingredient_type': 'Unit'}
                                 for _ in ingredients]}
    form = FullQuantityForm(data=data)  # List of dictionaries
    form.ingredients = ingredients
    if form.is_submitted():
        # user.grocery_list [{'Another Name': [['Bread Crumbs', 1, 'Unit', 0], ...], 'Alex': []}, overlap[int]]
        entries = []  # Extras list Format: [ [AisleName, [IngredientName, quantity, unit, BoolCheck]],...]
        unsorted = []
        aisles = Aisles.query.filter_by(user_id=current_user.id).all()
        for i, ingredient_form in enumerate(form.ingredient_forms):  # For item in user entered extras
            for j, aisle in enumerate(aisles):  # For aisle in user aisles
                if form.ingredients[i] in aisle.content.split(', ') and j <= len(aisles):  # If ingredient in that aisle
                    entries.append([aisle.title, [form.ingredients[i],
                                                  fraction_check(ingredient_form.ingredient_quantity.data, ingredients),
                                                  ingredient_form.ingredient_type.data, 0]])  # Add to extras
                    break
                else:  # All aisles have been searched, no matches
                    unsorted.append([form.ingredients[i],
                                     fraction_check(ingredient_form.ingredient_quantity.data, ingredients),
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


def fraction_check(num, ingredients):
    if num.count('/') == 1 and ''.join(i for i in num if i not in ['/', ' ']).isnumeric():
        num = num.split('/')
        return float(num[0]) / float(num[1])
    elif num.count('/') != 1:
        flash('Not a valid division')
        return redirect(url_for('main.add_extras', ingredients=json.dumps(ingredients)))
    else:
        try:
            return float(num)
        except ValueError:
            flash('Enter a number or a fraction')
            return redirect(url_for('main.add_extras', ingredients=json.dumps(ingredients)))


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


@main.route('/home/change_eaten', methods=['POST'])
def change_to_eaten():
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.filter_by(id=recipe_id).first()
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