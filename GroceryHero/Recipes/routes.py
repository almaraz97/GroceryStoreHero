import itertools
import json
import string
from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint, Response, session)
from flask_login import current_user, login_required
from GroceryHero import db
from GroceryHero.HarmonyToolCy import recipe_stack
from GroceryHero.Main.utils import update_grocery_list, get_harmony_settings, rem_trail_zero
from GroceryHero.Recipes.forms import RecipeForm, FullQuantityForm, RecipeLinkForm, Measurements
from GroceryHero.Recipes.utils import parse_ingredients
from GroceryHero.Users.forms import HarmonyForm
from GroceryHero.models import Recipes
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode

recipes = Blueprint('recipes', __name__)


@recipes.route('/recipes', methods=['GET', 'POST'])
def recipes_page(possible=0, recommended=None):
    if current_user.is_authenticated:
        recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()  # Get all recipes
        in_menu = [recipe for recipe in recipe_list if recipe.in_menu]  # Recipe objects that are in menu
        for i, recipe in enumerate(in_menu):  # Puts menu items first in recipe_list
            recipe_list.remove(recipe)
            recipe_list.insert(i, recipe)
        in_menu = [recipe.title for recipe in in_menu]  # List of recipe titles in menu
        recipe_history = [item for sublist in current_user.history[:current_user.harmony_preferences['history']]
                          for item in sublist]
        recipe_history = [x.title for x in Recipes.query.filter(Recipes.id.in_(recipe_history)).all()]
        # Recipe Harmony Tool Form
        form = HarmonyForm()
        form.groups.choices = [x for x in range(2 - len(in_menu), 5) if 0 < x]
        modifier = current_user.harmony_preferences['modifier']
        form.similarity.choices = [x for x in range(0, 60, 10)] + ['No Limit'] if modifier == 'True' else \
                                    [x for x in range(50, 105, 5)] + ['No Limit']
        form.similarity.default = 50
        excludes = [recipe.title for recipe in recipe_list if recipe.title not in (in_menu + recipe_history)]
        form.excludes.choices = [x for x in zip([0] + excludes, ['-- select options (clt+click) --'] + excludes)]
        recipe_ids = {recipe.title: recipe.id for recipe in recipe_list}
        colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
                  'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d', }
        about = None if current_user.pro else True
        if request.method == 'GET':
            # check_preferences(current_user)
            preferences = current_user.harmony_preferences  # Load user's previous preferences dictionary
            form.similarity.data = preferences['similarity']
            form.groups.data = preferences['groups']
            possible = preferences['possible']
            if preferences['recommended'] and preferences['recommended'] != '':  # If saved recommended is not empty
                recommended = {tuple(group.split(', ')): preferences['recommended'][group] for
                               group in preferences['recommended'] if tuple(group.split(', '))}
                # todo might be redundant, (prevent deleted recipes from being linked in a recommended)
                recommended = {key: value for key, value in recommended.items() if
                               all(x in [r.title for r in recipe_list] for x in key)}
        elif request.method == 'POST':  # Harmony or search button was pressed  # todo only on form submit
            preferences = get_harmony_settings(current_user.harmony_preferences)
            recipes = {r.title: r.quantity.keys() for r in recipe_list}
            count = int(form.groups.data)  # + len(in_menu) if form.groups.data else len(in_menu)
            recommended, possible = recipe_stack(recipes, count, max_sim=form.similarity.data,
                                                 excludes=form.excludes.data + recipe_history, includes=in_menu,
                                                 limit=1_000_000, **preferences)
            in_menu = None if len(in_menu) < 1 else in_menu  # Don't show menu items in recommendation groups
            if in_menu is not None:
                for group in list(recommended.keys()):
                    recommended[tuple([x for x in group if x not in in_menu])] = recommended[group]
                    del recommended[group]
            # Update user preferences
            preference = {key: current_user.harmony_preferences[key] for key in current_user.harmony_preferences}
            preference['similarity'] = form.similarity.data
            preference['groups'] = form.groups.data
            preference['recommended'] = {', '.join(list(group)): recommended[group] for group in recommended}
            preference['possible'] = possible
            current_user.harmony_preferences = preference
            db.session.commit()
        return render_template('recipes.html', title='Recipes', cards=recipe_list,
                               recipe_ids=recipe_ids,
                               search_recipes=sorted(recipe_list, key=lambda x: x.title), about=about,
                               sidebar=True, combos=possible, recommended=recommended, form=form, colors=colors)
    return render_template('recipes.html', recipes=None, all_recipes=None, title='Recipes', sidebar=False, combos=0,
                           recommended=None)


@recipes.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_recipe():
    if len(Recipes.query.filter_by(author=current_user).all()) > 75:  # User recipe limit
        return redirect(url_for('main.account'))
    form = RecipeForm()
    if form.validate_on_submit():  # Send data to quantity page
        ingredients = [string.capwords(x.strip()) for x in form.content.data.split(',') if x.strip() != '']
        ingredients = {ingredient: [1, 'Unit'] for ingredient in ingredients}
        session['recipe'] = {'title': string.capwords(form.title.data), 'quantity': ingredients,
                             'notes': form.notes.data, 'type': form.type_.data}
        return redirect(url_for('recipes.new_recipe_quantity'))
    return render_template('create_recipe.html', title='New Recipe', form=form, legend='New Recipe', link=True)


@recipes.route('/post/new/quantity', methods=['GET', 'POST'])
@login_required
def new_recipe_quantity():
    recipe = session['recipe']  # Has {RecipeName: string, Quantity: {ingredient: [value,type]}}
    data = {'ingredient_forms': [{'ingredient_quantity': recipe['quantity'][ingredient][0],
                                  'ingredient_type': recipe['quantity'][ingredient][1]}
                                 for ingredient in recipe['quantity'].keys()]}
    form = FullQuantityForm(data=data)
    form.ingredients = [x for x in recipe['quantity'].keys()]
    if form.validate_on_submit():
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [Q, M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}
        recipe = Recipes(title=(recipe['title']), quantity=formatted, author=current_user,
                         notes=recipe['notes'], recipe_type=recipe['type'])
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('recipes.recipes_page'))
    return render_template('recipe_quantity.html', title='New Recipe', form=form, legend='Recipe Quantities',
                           recipe=recipe)


@recipes.route('/recipes/link', methods=['GET', 'POST'])
@login_required
def recipe_from_link():
    form = RecipeLinkForm()
    if form.validate_on_submit():
        try:
            scraper = scrape_me(form.link.data)
        except WebsiteNotImplementedError:
            try:
                scraper = scrape_me(form.link.data, wild_mode=True)
            except NoSchemaFoundInWildMode:
                flash("Website not supported :/", 'danger')
                return redirect(url_for('recipes.recipe_from_link'))
        ingredients = [x.lower() for x in scraper.ingredients()]
        ings, quantity = parse_ingredients(ingredients)
        session['recipe_raw'] = {'title': scraper.title(), 'notes': scraper.instructions(), 'ingredients': ings,
                                 'measures': quantity}
        return redirect(url_for('recipes.new_recipe_link'))
    return render_template('recipe_link.html', title='New Recipe', legend='Recipe From Link', form=form)


@recipes.route('/post/new_link', methods=['GET', 'POST'])
@login_required
def new_recipe_link():  # filling out the form data from link page
    form = RecipeForm()
    if request.method == 'GET':
        if len(Recipes.query.filter_by(author=current_user).all()) > 75:  # User recipe limit
            return redirect(url_for('main.account'))
        recipe = session['recipe_raw']
        form.title.data = recipe['title']
        form.content.data = ', '.join([x.replace(',', '') for x in recipe['ingredients']])
        form.notes.data = recipe['notes']
    if form.validate_on_submit():  # Send data to quantity page
        ingredients = [string.capwords(x.strip()) for x in form.content.data.split(',') if x.strip() != '']
        ings = {}
        for i, ing in enumerate(ingredients):
            try:
                ings[ing] = session['recipe_raw']['measures'][i]
            except IndexError:
                ings[ing] = [1, 'Unit']
        ingredients = ings
        session['recipe'] = {'title': string.capwords(form.title.data), 'quantity': ingredients,
                             'notes': form.notes.data, 'type': form.type_.data}
        return redirect(url_for('recipes.new_recipe_quantity'))
    return render_template('create_recipe.html', title='New Recipe', form=form, legend='New Recipe')


@recipes.route('/post/<int:recipe_id>/update', methods=['GET', 'POST'])
@login_required
def update_recipe(recipe_id):
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only update your own recipes
        abort(403)
    form = RecipeForm()
    if form.validate_on_submit():
        ingredients = sorted([string.capwords(x.strip()) for x in form.content.data.split(',')])
        quantity_dict = {ingredient: recipe.quantity[ingredient] if ingredient in recipe.quantity else [1, 'Unit']
                         for ingredient in ingredients}
        notes = form.notes.data
        title = string.capwords(form.title.data.strip())
        session['recipe'] = {'title': title, 'quantity': quantity_dict, 'notes': notes, 'type':form.type_.data}
        return redirect(url_for('recipes.update_recipe_quantity', recipe_id=recipe_id))
    elif request.method == 'GET':
        form.title.data = recipe.title
        form.content.data = ', '.join(recipe.quantity.keys())
        form.notes.data = recipe.notes
        form.type_.data = recipe.recipe_type
    return render_template('create_recipe.html', title='Update Recipe', form=form, legend='Update Recipe')  # todo


@recipes.route('/post/<int:recipe_id>/update_quantity', methods=['GET', 'POST'])
@login_required
def update_recipe_quantity(recipe_id):
    recipe = session['recipe']  # Has {RecipeName: string, Quantity: {ingredient: [value,type]}}
    data = {'ingredient_forms': [{'ingredient_quantity': recipe['quantity'][ingredient][0],
                                  'ingredient_type': recipe['quantity'][ingredient][1]}
                                 for ingredient in recipe['quantity'].keys()]}
    form = FullQuantityForm(data=data)  # List of dictionaries
    form.ingredients = [x for x in recipe['quantity'].keys()]

    if form.validate_on_submit():
        formatted = {ingredient: [F['ingredient_quantity'], F['ingredient_type']] for ingredient, F in
                     zip(form.ingredients, form.ingredient_forms.data)}
        # Get previous data to update
        rec = Recipes.query.get_or_404(recipe_id)
        rec.title = recipe['title']
        rec.quantity = formatted  # Must be different to change to alphabetical
        rec.notes = recipe['notes']
        rec.recipe_type = recipe['type']
        update_grocery_list(current_user)
        db.session.commit()
        flash('Your recipe has been updated!', 'success')
        return redirect(url_for('recipes.recipe_single', recipe_id=rec.id))
    return render_template('recipe_quantity.html', title='Update Recipe', form=form, legend='Recipe Quantities',
                           recipe=recipe)


@recipes.route('/post/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def recipe_single(recipe_id):
    recipe_post = Recipes.query.get_or_404(recipe_id)
    if recipe_post.author != current_user:
        abort(403)
    quantity = {ingredient: [rem_trail_zero(recipe_post.quantity[ingredient][0]), recipe_post.quantity[ingredient][1]]
                for ingredient in recipe_post.quantity}
    recipe_post.quantity = quantity
    if request.method == 'POST':  # Download recipe
        title = recipe_post.title
        recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
        return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
                                                                 f"attachment; filename={title}.txt"})
    return render_template('recipe.html', title=recipe_post.title, recipe=recipe_post)


@recipes.route('/post/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only change your own recipes
        abort(403)
    db.session.delete(recipe)
    if recipe.title in current_user.harmony_preferences['recommended']:  # If delete recipe in recommended
        temp = {key: value for key, value in current_user.harmony_preferences.items()}
        temp['recommended'] = {}  # Reset recipe tool recommendations
        temp['possible'] = 0
        current_user.harmony_preferences = temp
    update_grocery_list(current_user)
    db.session.commit()
    flash('Your recipe has been deleted!', 'success')
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/recipes/change_menu', methods=['POST'])
@login_required
def change_to_menu():  # JavaScript way of adding to menu without reload
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only update your own recipes # Might not be needed
        abort(403)
    recipe.in_menu = not recipe.in_menu
    update_grocery_list(current_user)
    db.session.commit()
    return json.dumps({'result': 'success'})


@recipes.route('/recipes/<int:recipe_id>/add_menu', methods=['GET', 'POST'])  # ??REQUIRES 'GET'
@login_required
def add_to_menu(recipe_id):  # Adding from RHT recommendations
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only update your own recipes # Might not be needed
        abort(403)
    recipe.in_menu = True
    update_grocery_list(current_user)
    db.session.commit()
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/recipes/multi_add_menu/', methods=['GET', 'POST'])  # From Recipe Harmony Tool Multi-select
@login_required
def multi_add_to_menu():
    for recipe_id in request.form.getlist('harmony'):
        recipe = Recipes.query.get_or_404(recipe_id)
        if recipe.author != current_user:  # You can only add your own recipes # Might not be needed
            abort(403)
        recipe.in_menu = True
    update_grocery_list(current_user)
    db.session.commit()
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/recipes/multi_add_menu2/<ids>', methods=['GET', 'POST'])  # From Recipe Harmony Tool <ul> group
@login_required
def multi_add_to_menu2(ids=None):
    ids = json.loads(ids)
    if ids is None or ids == '':
        return redirect(url_for('recipes.recipes_page'))  # Potential bug
    for recipe_id in ids:
        recipe = Recipes.query.get_or_404(recipe_id)
        if recipe.author != current_user:  # You can only add your own recipes # Might not be needed
            abort(403)
        recipe.in_menu = True
    update_grocery_list(current_user)
    db.session.commit()
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/post/search', methods=['GET', 'POST'])
@login_required
def recipes_search(recommended=None, possible=0):
    if current_user.is_authenticated:
        search = request.form['search']
        if search == 'Recipe Options' or search == '':
            return redirect(url_for('recipes.recipes_page'))
        recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()  # Get all recipes
        all_rec = sorted(recipe_list, key=lambda x: x.title)
        ids = {recipe.title: recipe.id for recipe in recipe_list}
        cards = [recipe for recipe in recipe_list if search.lower() in recipe.title.lower()]
        # Sidebar form
        # form = HarmonyForm()
        # choices = [recipe.title for recipe in recipe_list if not recipe.in_menu]  # Can't exclude menu items
        # form.excludes.choices = [x for x in zip([0] + choices, ['-- select options (clt+click) --'] + choices)]
        # if request.method == 'POST':  # Load previous preferences/recommendations
        #     preference = current_user.harmony_preferences  # Preference dictionary
        #     form.similarity.data = preference['similarity']
        #     form.groups.data = preference['groups']
        #     possible = preference['possible']
        #     if preference['recommended']:  # If saved recommended is not empty
        #         recommended = {tuple(group.split(', ')): preference['recommended'][group] for
        #                        group in preference['recommended']}
        return render_template('recipes.html', title='Recipes', cards=cards, recipe_ids=ids, search_recipes=all_rec)
        # form=form, sidebar=True, combos=possible, recommended=recommended,


@recipes.route('/recipe_similarity/<ids>/<sim>', methods=['GET', 'POST'])
@login_required
def recipe_similarity(ids, sim):  # Too similar button in recommendations
    ids = json.loads(ids)
    recipe_names = [Recipes.query.filter_by(id=ID).first().title for ID in ids]
    recipe_names = [x for x in recipe_names if x is not None]
    dictionary = current_user.harmony_preferences.copy()
    if isinstance(dictionary['tastes'], str):  # If the entries are JSON for some reason?
        dictionary['tastes'] = json.loads(dictionary['tastes'])
    for combo in itertools.combinations(recipe_names, 2):
        combo = str(str(combo[0]) + ', ' + str(combo[1]))
        if combo not in dictionary['tastes']:  # Not in preferences yet
            if float(sim) == 1.0:  # Don't add redundant weight
                pass
            else:
                dictionary['tastes'][combo] = str(sim)
        else:  # Weight is changing
            if float(sim) == 1.0:  # Remove from preferences since redundant
                del dictionary['tastes'][combo]
            else:  # Else change the weight
                dictionary['tastes'][combo] = str(sim)
    dictionary['tastes'] = json.dumps(dictionary['tastes'])
    current_user.harmony_preferences = dictionary
    db.session.commit()
    return redirect(url_for('recipes.recipes_page'))


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

# @recipes.route('/post/<int:recipe_id>/download', methods=['GET', 'POST'])
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
