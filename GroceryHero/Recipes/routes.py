import itertools
import json
import string
from datetime import datetime

from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint, Response, session)
from flask_login import current_user, login_required
from GroceryHero import db
from GroceryHero.HarmonyTool import recipe_stack
from GroceryHero.Main.utils import update_grocery_list, get_harmony_settings, rem_trail_zero
from GroceryHero.Recipes.forms import RecipeForm, FullQuantityForm, RecipeLinkForm, Measurements
from GroceryHero.Recipes.utils import parse_ingredients
from GroceryHero.Users.forms import HarmonyForm
from GroceryHero.models import Recipes, User, Followers, Actions, Pub_Rec, User_Rec
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode

recipes = Blueprint('recipes', __name__)


@recipes.route('/recipes', methods=['GET', 'POST'])
def recipes_page(possible=0, recommended=None):
    if current_user.is_authenticated:  # todo allow borrowed recipe to be put on menu and display it correctly
        followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
        friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
        recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()  # Get all recipes
        borrows = {x.recipe_id: x.in_menu for x in
                    User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}
        in_menu = [recipe for recipe in recipe_list if recipe.in_menu]  # Recipe objects that are in menu
        in_menu = in_menu + Recipes.query.filter(Recipes.id.in_([x for x in borrows.keys() if borrows[x]])).all()
        borrowed = Recipes.query.filter(Recipes.id.in_(borrows.keys())).all()
        recipe_list = sorted(recipe_list + borrowed, key=lambda x: x.title)
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
                  'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
        # about, harmony = (None, True) if current_user.pro else (True, None)
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
        return render_template('recipes.html', title='Recipes', cards=recipe_list, recipe_ids=recipe_ids,
                               search_recipes=recipe_list, about=about, sidebar=True, combos=possible,
                               recommended=recommended, form=form, colors=colors, borrows=borrows, friend_dict=friend_dict)
    return render_template('recipes.html', recipes=None, all_recipes=None, title='Recipes', sidebar=False, combos=0,
                           recommended=None)


@recipes.route('/friend_recipes', methods=['GET', 'POST'])
@login_required
def friend_recipes():  # todo handle deleted account ids
    colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
              'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
    recipe_list = []
    borrows = {x.recipe_id: x.borrowed for x in
               User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}
    user_recipes = Recipes.query.filter_by(author=current_user).all()
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    borrowed_list = []
    for friend in followees:  # Add their recipes to recipe_list
        for recipe in Recipes.query.filter_by(user_id=friend).all():
            if recipe not in user_recipes:
                borrowed_list.append(recipe) if recipe.id in borrows else recipe_list.append(recipe)
    recipe_list = sorted(recipe_list, key=lambda x: x.date_created)
    recipe_list = recipe_list + borrowed_list
    return render_template('recipes.html', recipes=None, cards=recipe_list, title='Friend Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list, borrows=borrows,
                           friend_dict=friend_dict, all_friends=friend_dict, friends=True, switch=True)


@recipes.route('/public_recipes', methods=['GET', 'POST'])
@login_required
def public_recipes():  # todo handle deleted account ids
    colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
              'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
    recipe_list = [x for x in Pub_Rec.query.all()]
    recipe_list = sorted(recipe_list, key=lambda x: x.date_created)
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    return render_template('recipes.html', recipes=None, cards=recipe_list, title='Public Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list,
                           friend_dict=friend_dict, all_friends=friend_dict, friends=True, public=True)


@recipes.route('/friend_recipes/<int:friend>', methods=['GET', 'POST'])
@login_required
def friend_recipes_choice(friend=None):  # todo handle deleted account ids
    if friend is None or friend == current_user.id:
        return redirect(url_for('recipes.friend_recipes'))
    colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
              'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
    followee = Followers.query.filter_by(user_id=current_user.id, follow_id=friend).first()
    all_followees = Followers.query.filter_by(user_id=current_user.id).all()
    all_friends = {F.follow_id: User.query.filter_by(id=F.follow_id).first()
                   for F in all_followees if F.status == 1}
    borrows = {x.recipe_id: x.in_menu for x in
               User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}
    if followee.status == 1:
        user_recipes = Recipes.query.filter_by(author=current_user).all()
        friend = User.query.filter_by(id=friend).first()
        friend_dict = {friend.id: friend}
        recipe_list = [x for x in Recipes.query.filter_by(user_id=friend.id).all() if x not in user_recipes]
        recipe_list = sorted(recipe_list, key=lambda x: x.date_created)
    else:
        return redirect(url_for('recipes.friend_recipes'))
    return render_template('recipes.html', recipes=None, cards=recipe_list, title='Friend Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list, borrows=borrows,
                           friend_dict=friend_dict, all_friends=all_friends, friends=True)


@recipes.route('/friend_feed', methods=['GET', 'POST'])
@login_required
def friend_feed():  # todo pagination for posts or limit by date?
    colors = {'Delete': '#dc3545', 'Add': '#5cb85c', 'Update': '#20c997', 'Clear': '#6610f2', 'Borrow': '#17a2b8',
              'Unborrow': '#6c757d'}
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    cards = sorted(Actions.query.filter(Actions.user_id.in_(followees)).all(), key=lambda x: x.date_created, reverse=True)
    # Get friend recipe dict(id:Recipe) to hyperlink their 'Clear' actions
    recs = [item for sublist in [r.recipe_ids for r in cards] for item in sublist]
    recs = Recipes.query.filter(Recipes.id.in_(recs)).all()
    rec_dict = {r.id: r for r in recs}
    all_friend_recs = {x.id: x for x in Recipes.query.filter(Recipes.user_id.in_(followees)).all()}
    return render_template('friend_feed.html', rec_dict=rec_dict, cards=cards, title='Friend Feed', sidebar=True, #search=None
                           colors=colors, friend_dict=friend_dict, all_friends=friend_dict, friends=True, feed=True,
                           all_friend_recs=all_friend_recs)


@recipes.route('/friend_feed/<int:friend_id>', methods=['GET', 'POST'])
@login_required
def friend_feed_choice(friend_id=None):
    if friend_id is None:
        return redirect(url_for('recipes.friend_feed'))
    # {'yellow': '#ffc107', 'pink': '#e83e8c', 'secondary': '#6c757d'}
    colors = {'Delete': '#dc3545', 'Add': '#5cb85c', 'Update': '#20c997', 'Clear': '#6610f2', 'Borrow': '#17a2b8',
              'Unborrow': '#6c757d'}
    followee = Followers.query.filter_by(user_id=current_user.id, follow_id=friend_id).first()
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    if followee.status == 1:
        followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
        all_friends = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
        # friend = User.query.filter_by(id=followee.follow_id).all()
        # friend_dict = {friend.id: friend.username}
        cards = Actions.query.filter_by(user_id=followee.follow_id).all()
        cards = sorted(cards, key=lambda x: x.date_created, reverse=True)
        recs = [item for sublist in [r.recipe_ids for r in cards if r.type_ == 'Clear'] for item in sublist]
        recs = Recipes.query.filter(Recipes.id.in_(recs)).all()
        rec_dict = {r.id: r for r in recs}
    else:
        return redirect(url_for('recipes.friend_recipes'))
    return render_template('friend_feed.html', recipes=None, cards=cards, title='Friend Feed', sidebar=True, rec_dict=rec_dict,
                           colors=colors, all_friends=all_friends, friend_dict=friend_dict, friends=True, feed=True)


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
                         notes=recipe['notes'], recipe_type=recipe['type'], link=recipe.get('link', ''))
        db.session.add(recipe)
        db.session.commit()  # todo does recipe have ID before commit()?
        action = Actions(user_id=current_user.id, type_='Add', recipe_ids=[recipe.id], date_created=datetime.utcnow(),
                         titles=[recipe.title])
        db.session.add(action)
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
                                 'measures': quantity, 'link': form.link.data if len(form.link.data) <= 20 else ''}
        return redirect(url_for('recipes.new_recipe_link'))  # todo change link string limit
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
            # todo figure out how to link quantity with ingredients, despite deletion and modification
            ings[ing] = session['recipe_raw']['measures'][i]  # except IndexError: ings[ing] = [1, 'Unit']

        session['recipe'] = {'title': string.capwords(form.title.data), 'quantity': ings,
                             'notes': form.notes.data, 'type': form.type_.data, 'link': session['recipe_raw']['link']}
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
        session['recipe'] = {'title': title, 'quantity': quantity_dict, 'notes': notes, 'type': form.type_.data}
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
        action = Actions(user_id=current_user.id, type_='Update', recipe_ids=[recipe_id],
                         date_created=datetime.utcnow(), titles=[rec.title])
        db.session.add(action)
        db.session.commit()
        flash('Your recipe has been updated!', 'success')
        return redirect(url_for('recipes.recipe_single', recipe_id=rec.id))
    return render_template('recipe_quantity.html', title='Update Recipe', form=form, legend='Recipe Quantities',
                           recipe=recipe)


@recipes.route('/post/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def recipe_single(recipe_id):
    recipe_post = Recipes.query.get_or_404(recipe_id)
    quantity = {ingredient: [rem_trail_zero(recipe_post.quantity[ingredient][0]), recipe_post.quantity[ingredient][1]]
                for ingredient in recipe_post.quantity}  # todo is this still necessary?
    recipe_post.quantity = quantity
    if request.method == 'POST':  # Download recipe
        if recipe_post.user_id == current_user.id:
            title = recipe_post.title
            recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
            return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
                                                                     f"attachment; filename={title}.txt"})
        else:
            return redirect(url_for('recipes.recipe_borrow', recipe_id=recipe_id))
    return render_template('recipe.html', title=recipe_post.title, recipe=recipe_post, recipe_single=True, sidebar=True)


@recipes.route('/borrow/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def recipe_borrow(recipe_id):
    recipe_post = Recipes.query.get_or_404(recipe_id)
    if recipe_post.user_id == current_user.id:  # todo redirect should be better
        return render_template('recipe.html', title=recipe_post.title, recipe=recipe_post)
    else:
        borrowed = User_Rec.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if borrowed is not None:  # If user currently has history with recipe
            if borrowed.borrowed:
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = False, False, False
                borrowed.borrowed_dates['Unborrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
                flash(f"You have returned {recipe_post.title}", 'info')
                if len(borrowed.borrowed_dates['Unborrowed']) == 1:  # First time unborrowing
                    action = Actions(user_id=current_user.id, type_='Unborrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe_post.title])
                    db.session.add(action)
            else:  # Not currently borrowed
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = True, False, False
                borrowed.borrowed_dates['Borrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
                flash(f"{recipe_post.title} borrowed!", 'success')
                if len(borrowed.borrowed_dates['Unborrowed']) == 1:  # First time borrowing
                    action = Actions(user_id=current_user.id, type_='borrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe_post])
                    db.session.add(action)
        else:  # Create new borrow
            borrow = User_Rec(user_id=current_user.id, recipe_id=recipe_id, borrowed=True,
                              borrowed_dates={'Borrowed': [datetime.utcnow().strftime('%Y-%m-%d-%H-%M')], 'Unborrowed': []})
            flash(f"{recipe_post.title} borrowed!", 'success')
            action = Actions(user_id=current_user.id, type_='Borrow', recipe_ids=[recipe_id],
                             date_created=datetime.utcnow(), titles=[recipe_post.title])
            db.session.add(action)
            db.session.add(borrow)
        db.session.commit()
    return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))


@recipes.route('/post/search', methods=['GET', 'POST'])
@login_required
def recipes_search(recommended=None, possible=0):
    if current_user.is_authenticated:
        search = request.form['search']
        if search == 'Recipe Options' or search == '':
            return redirect(url_for('recipes.recipes_page'))
        colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
                  'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
        followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
        friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
        recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()  # Get all recipes
        borrows = {x.recipe_id: x.in_menu for x in
                  User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}
        borrowed = Recipes.query.filter(Recipes.id.in_(borrows.keys())).all()
        all_rec = sorted(recipe_list + borrowed, key=lambda x: x.title)
        recipe_list = recipe_list + borrowed
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
        return render_template('recipes.html', title='Recipes', cards=cards, recipe_ids=ids, search_recipes=all_rec,
                               colors=colors, borrows=borrows, friend_dict=friend_dict)
        # form=form, sidebar=True, combos=possible, recommended=recommended,


@recipes.route('/post/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only change your own recipes
        abort(403)
        return redirect(url_for('recipes.recipes_page'))
    db.session.delete(recipe)
    if recipe.title in current_user.harmony_preferences['recommended']:  # If delete recipe in recommended
        temp = {key: value for key, value in current_user.harmony_preferences.items()}
        temp['recommended'] = {}  # Reset recipe tool recommendations
        temp['possible'] = 0
        current_user.harmony_preferences = temp
    update_grocery_list(current_user)
    action = Actions(user_id=current_user.id, type_='Delete', recipe_ids=[recipe_id],
                     date_created=datetime.utcnow(), titles=[recipe.title])
    db.session.add(action)
    db.session.commit()
    flash('Your recipe has been deleted!', 'success')
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/recipes/change_menu', methods=['POST'])
@login_required
def change_to_menu():  # JavaScript way of adding to menu without reload
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        recipe = User_Rec.query.get([current_user.id, recipe_id])
        if recipe is None:
            json.dumps({'result': 'success'})
    recipe.in_menu = not recipe.in_menu
    recipe.eaten = False
    update_grocery_list(current_user)
    db.session.commit()
    return json.dumps({'result': 'success'})


@recipes.route('/recipes/change_borrow', methods=['POST'])
@login_required
def change_to_borrow():  # JavaScript way of adding to menu without reload
    recipe_id = request.form['recipe_id']
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        title = recipe.title.copy()
        recipe = User_Rec.query.get([current_user.id, recipe_id])
        if recipe is None:  # If user hasn't borrowed this recipe before make new entry
            user_id = current_user.id
            borrow = User_Rec(user_id=user_id, recipe_id=recipe_id, borrowed=True,
                              borrowed_dates={'Borrowed': [datetime.utcnow().strftime('%Y-%m-%d-%H-%M')], 'Unborrowed': []})
            action = Actions(user_id=user_id, type_='Borrow', recipe_ids=[recipe_id], date_created=datetime.utcnow(),
                             titles=[title])
            db.session.add(action)
            db.session.add(borrow)
            db.session.commit()
            return json.dumps({'result': 'success'})
        # Person has borrowed this recipe before (entry exists)
        recipe.borrowed = not recipe.borrowed
        if recipe.borrowed:  # Now Borrowed
            recipe.borrowed_dates['Borrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
        else:  # Now Unborrowed
            recipe.borrowed_dates['Unborrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
        recipe.in_menu = False
        recipe.eaten = False
        db.session.commit()
    return json.dumps({'result': 'success'})


@recipes.route('/recipes/<int:recipe_id>/add_menu', methods=['GET', 'POST'])  # ??REQUIRES 'GET'
@login_required
def add_to_menu(recipe_id):  # Adding from RHT recommendations
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        recipe = User_Rec.query.get([current_user.id, recipe_id])
        if recipe is None:
            json.dumps({'result': 'success'})
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
            recipe = User_Rec.query.get([current_user.id, recipe_id])
            if recipe is None:  # User added to menu a not borrowed recipe??
                continue
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
        if recipe.author != current_user:
            recipe = User_Rec.query.get([current_user.id, recipe_id])
            if recipe is None:  # User added to menu a not borrowed recipe??
                continue
        recipe.in_menu = True
    update_grocery_list(current_user)
    db.session.commit()
    return redirect(url_for('recipes.recipes_page'))


@recipes.route('/recipe_similarity/<ids>/<sim>', methods=['GET', 'POST'])
@login_required
def recipe_similarity(ids, sim):  # The too similar button in recommendations
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