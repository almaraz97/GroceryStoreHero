import itertools
import json
import string
from datetime import datetime, timedelta
from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint, Response, session, current_app)
from flask_login import current_user, login_required
from GroceryHero import db
from GroceryHero.Main.utils import update_grocery_list, get_harmony_settings, rem_trail_zero
from GroceryHero.Recipes.forms import RecipeForm, FullQuantityForm, RecipeLinkForm, UploadRecipeImage
from GroceryHero.Recipes.utils import parse_ingredients, generate_feed_contents, get_friends, get_recipes, \
    remove_menu_items, recipe_stack_w_args, update_user_preferences, load_harmonyform, load_quantityform
from GroceryHero.Users.forms import HarmonyForm
from GroceryHero.Users.utils import save_picture, Colors
from GroceryHero.models import Recipes, User, Followers, Actions, Pub_Rec, User_Rec
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode

recipes = Blueprint('recipes', __name__)


@login_required
@recipes.route('/recipes', methods=['GET', 'POST'])
def recipes_page(possible=0, recommended=None):
    recipe_history, form, about, colors = [], HarmonyForm(), True, Colors.rec_colors
    followees, friend_dict = get_friends(current_user)
    recipe_list, borrows, in_menu, recipe_ids = get_recipes(current_user)
    in_menu = [r.title for r in in_menu]
    about = None if current_user.pro else True
    preferences = get_harmony_settings(current_user.harmony_preferences)
    if request.method == "GET":
        form, recommended, recipe_history, possible = load_harmonyform(current_user, form, in_menu, recipe_list)
    if request.method == "POST":
        if form.validate_on_submit():  # Harmony or search button was pressed
            recommended, possible = recipe_stack_w_args(recipe_list, preferences, form, in_menu, recipe_history)
            recommended = remove_menu_items(in_menu, recommended)
            update_user_preferences(current_user, form, recommended, possible)
            form, recommended, recipe_history, possible = load_harmonyform(current_user, form, in_menu, recipe_list)
    return render_template('recipes.html', title='Recipes', cards=recipe_list, recipe_ids=recipe_ids,
                           search_recipes=recipe_list, about=about, sidebar=True, combos=possible,
                           recommended=recommended, form=form, colors=colors, borrows=borrows, friend_dict=friend_dict)


@login_required
@recipes.route('/recipes/search', methods=['GET', 'POST'])
def recipes_search(possible=0, recommended=None):
    if current_user.is_authenticated:
        search = request.form['search']
        if search == 'Recipe Options' or search == '':
            return redirect(url_for('recipes.recipes_page'))
        colors = {'Breakfast': '#5cb85c', 'Lunch': '#17a2b8', 'Dinner': '#6610f2',
                  'Dessert': '#e83e8c', 'Snack': '#ffc107', 'Other': '#6c757d'}
        followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]  # todo replace
        friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
        recipe_list = Recipes.query.filter_by(author=current_user).order_by(Recipes.title).all()  # Get all recipes  # TODO replace
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


@login_required
@recipes.route('/recipes/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_single(recipe_id):
    recipe_post = Recipes.query.get_or_404(recipe_id)
    form = UploadRecipeImage()
    quantity = {ingredient: [rem_trail_zero(recipe_post.quantity[ingredient][0]), recipe_post.quantity[ingredient][1]]
                for ingredient in recipe_post.quantity}  # todo is this still necessary?
    recipe_post.quantity = quantity
    url = recipe_post.picture
    url = url if url is not None else False  # todo might not be neccesary
    # eaten and borrowed by others
    others_eaten = sum(x.times_eaten for x in User_Rec.query.filter_by(recipe_id=recipe_id).all())
    others_borrowed = sum(1 for x in User_Rec.query.filter_by(recipe_id=recipe_id).all() if x.borrowed)
    other_downloaded = sum(1 for x in User_Rec.query.filter_by(recipe_id=recipe_id).all() if x.downloaded)
    borrowed = True
    if recipe_post.author != current_user:
        borrow = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
        borrowed = False if borrow is None else borrow.borrowed
    if request.method == 'POST':  # Download recipe
        if form.validate_on_submit() and (recipe_post.author == current_user) and form.picture.data:
            picture_file = save_picture(form.picture.data, filepath='static/recipe_pics')
            recipe_post.picture = picture_file
            db.session.commit()
            flash('Your image has been uploaded!', 'success')
            return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
        if recipe_post.user_id == current_user.id:
            title = recipe_post.title
            recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
            return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
                                                                     f"attachment; filename={title}.txt"})
        else:  # POST on recipe single borrows if not same user
            return redirect(url_for('recipes.recipe_borrow', recipe_id=recipe_id))
    return render_template('recipe.html', title=recipe_post.title, recipe=recipe_post, recipe_single=True, sidebar=True,
                           url=url, form=form, others_eaten=others_eaten, others_borrowed=others_borrowed,
                           other_downloaded=other_downloaded, borrowed=borrowed)


@login_required
@recipes.route('/friend_recipes', methods=['GET', 'POST'])
def friend_recipes():  # todo handle deleted account ids
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    colors = Colors.rec_colors
    recipe_list = []
    borrows = {x.recipe_id: x.borrowed for x in
               User_Rec.query.filter_by(user_id=current_user.id).all() if x.borrowed}
    user_recipes = Recipes.query.filter_by(author=current_user).all()
    followees, friend_dict = get_friends(current_user)
    borrowed_list = []
    for friend in followees:  # Add their recipes to recipe_list
        for recipe in Recipes.query.filter_by(user_id=friend).all():
            if recipe not in user_recipes:
                borrowed_list.append(recipe) if recipe.id in borrows else recipe_list.append(recipe)
    recipe_list = sorted(recipe_list, key=lambda x: x.date_created, reverse=True)
    recipe_list = recipe_list + borrowed_list
    return render_template('recipes.html', recipes=None, cards=recipe_list, title='Friend Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list, borrows=borrows,
                           friend_dict=friend_dict, all_friends=friend_dict, friends=True, switch=True)


@login_required
@recipes.route('/friend_recipes/<int:friend>', methods=['GET', 'POST'])
def friend_recipes_choice(friend=None):
    if friend is None or friend == current_user.id:
        return redirect(url_for('recipes.friend_recipes'))
    followee = Followers.query.filter_by(user_id=current_user.id, follow_id=friend).first()
    if followee is None:
        return redirect(url_for('recipes.friend_recipes'))
    colors = Colors.rec_colors
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
        recipe_list = sorted(recipe_list, key=lambda x: x.date_created, reverse=True)
    else:
        return redirect(url_for('recipes.friend_recipes'))
    return render_template('recipes.html', recipes=None, cards=recipe_list, title='Friend Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list, borrows=borrows,
                           friend_dict=friend_dict, all_friends=all_friends, friends=True)


@login_required
@recipes.route('/public_recipes', methods=['GET', 'POST'])
def public_recipes():
    colors = Colors.rec_colors
    user_id = current_user.id
    recipe_list = [x for x in Pub_Rec.query.all() if x.user_id != user_id]
    recipe_list = sorted(recipe_list, key=lambda x: x.date_created, reverse=True)
    followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in followees}
    return render_template('recipes_public.html', recipes=None, cards=recipe_list, title='Public Recipes', sidebar=True,
                           recommended=None,  colors=colors, search_recipes=recipe_list,
                           friend_dict=friend_dict, all_friends=friend_dict, friends=True, public=True)


@login_required
@recipes.route('/friend_feed', methods=['GET', 'POST'])
def friend_feed():
    colors = Colors.act_colors
    friend = request.args.get('friend', 0, type=int)
    all_followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    followees = all_followees if friend == 0 else [friend]
    if followees[0] not in all_followees:
        return redirect(url_for('recipes.friend_feed'))
    # if current_app.server:
    #   followees = followees + [current_user.id]
    friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in all_followees}
    page = request.args.get('page', 1, type=int)
    friend_acts = Actions.query.filter(Actions.user_id.in_(followees))\
        .order_by(Actions.date_created.desc()).paginate(page=page, per_page=10)
    cards = generate_feed_contents(friend_acts.items)
    return render_template('friend_feed.html', cards=cards, title='Friend Feed', sidebar=True,
                           colors=colors, friend_dict=friend_dict, all_friends=friend_dict,
                           friend_acts=friend_acts, friend=friend, page=page, friends=True, feed=True)


@login_required
@recipes.route('/recipes/new', methods=['GET', 'POST'])
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


@login_required
@recipes.route('/recipes/new/quantity', methods=['GET', 'POST'])
def new_recipe_quantity():
    recipe = session['recipe']  # {RecipeName: string, Quantity: {ingredient: [value,type]}}
    form = load_quantityform(recipe)
    if form.validate_on_submit():
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [Q, M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}
        pic_fn = save_picture(recipe.get('im_path', None), 'static/recipe_pics', download=True)
        pic_fn = pic_fn if pic_fn is not None else ''
        recipe = Recipes(title=(recipe['title']), quantity=formatted, author=current_user,
                         notes=recipe['notes'], recipe_type=recipe['type'], link=recipe.get('link', ''),
                         picture=pic_fn)
        db.session.add(recipe)
        db.session.commit()
        action = Actions(user_id=current_user.id, type_='Add', recipe_ids=[recipe.id], date_created=datetime.utcnow(),
                         titles=[recipe.title])
        db.session.add(action)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('recipes.recipes_page'))
    return render_template('recipe_quantity.html', title='New Recipe', form=form, legend='Recipe Quantities',
                           recipe=recipe)


@login_required
@recipes.route('/recipes/link', methods=['GET', 'POST'])
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
        im_path = scraper.image()
        session['recipe_raw'] = {'title': scraper.title(), 'notes': scraper.instructions(), 'ingredients': ings,
                                 'measures': quantity, 'link': form.link.data if len(form.link.data) <= 20 else '',
                                 'im_path': im_path}
        return redirect(url_for('recipes.new_recipe_link'))  # todo change link string limit
    return render_template('recipe_link.html', title='New Recipe', legend='Recipe From Link', form=form)


@login_required
@recipes.route('/recipes/new_link', methods=['GET', 'POST'])
def new_recipe_link():  # filling out the form data from link page
    form = RecipeForm()
    if request.method == 'GET':
        if len(current_user.recipes) > 75:  # User recipe limit
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
                             'notes': form.notes.data, 'type': form.type_.data, 'link': session['recipe_raw']['link'],
                             'im_path': session['recipe_raw']['im_path']}
        return redirect(url_for('recipes.new_recipe_quantity'))
    return render_template('create_recipe.html', title='New Recipe', form=form, legend='New Recipe')


@login_required
@recipes.route('/recipes/<int:recipe_id>/update', methods=['GET', 'POST'])
def update_recipe(recipe_id):
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user or recipe.public:  # You can only update your own recipes
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


@login_required
@recipes.route('/recipes/<int:recipe_id>/update_quantity', methods=['GET', 'POST'])
def update_recipe_quantity(recipe_id):
    rec = Recipes.query.get_or_404(recipe_id)
    if rec.author != current_user or rec.public:  # You can only update your own recipes
        abort(403)
    recipe = session['recipe']  # Has {RecipeName: string, Quantity: {ingredient: [value,type]}}
    form = load_quantityform(recipe)
    if form.validate_on_submit():
        formatted = {ingredient: [F['ingredient_quantity'], F['ingredient_type']] for ingredient, F in
                     zip(form.ingredients, form.ingredient_forms.data)}
        # Get previous data to update
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


@login_required
@recipes.route('/recipes/<int:recipe_id>/download', methods=['GET', 'POST'])
def recipe_download(recipe_id):
    all_recipes = Recipes.query.filter_by(author=current_user).all()
    recipe = Recipes.query.filter_by(id=recipe_id).first()
    for r in all_recipes:
        if recipe == r:
            flash(f'Recipe {recipe.title} already in recipe library', 'danger')
            return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
    new_recipe = Recipes(title=recipe.title, quantity=recipe.quantity, notes=recipe.notes, user_id=current_user.id,
                         link=recipe.link, recipe_type=recipe.recipe_type, recipe_genre=recipe.recipe_genre,
                         picture=recipe.picture, servings=recipe.servings, originator=recipe.originator,
                         price=recipe.price, options=recipe.options)
    db.session.add(recipe)
    db.session.commit()
    user_rec = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    if user_rec is None:
        user_rec = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id, downloaded=True)
        user_rec.downloaded_dates.append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
        db.session.add(user_rec)
    if not user_rec.downloaded:  # user hasn't downloaded this recipe before
        action = Actions(user_id=current_user.id, type_='Download', recipe_ids=[new_recipe.id], date_created=datetime.utcnow(),
                         titles=[new_recipe.title])
        db.session.add(action)
    db.session.commit()
    flash(f'{recipe.title} added to your library!', 'success')
    return redirect(url_for('recipes.recipe_single', recipe_id=new_recipe.id))


@login_required
@recipes.route('/borrow/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_borrow(recipe_id):  # From single page to borrowing the recipe
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.user_id == current_user.id:
        return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
    else:
        borrowed = User_Rec.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if borrowed is not None:  # If user currently has history with recipe  # todo move logic to utils
            if borrowed.borrowed:
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = False, False, False
                borrowed.borrowed_dates['Unborrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
                flash(f"You have returned {recipe.title}", 'info')
                if len(borrowed.borrowed_dates['Unborrowed']) == 1:  # First time unborrowing
                    action = Actions(user_id=current_user.id, type_='Unborrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe.title])
                    db.session.add(action)
            else:  # Not currently borrowed
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = True, False, False
                borrowed.borrowed_dates['Borrowed'].append(datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
                flash(f"{recipe.title} borrowed!", 'success')
                if len(borrowed.borrowed_dates['Borrowed']) == 1:  # First time borrowing
                    action = Actions(user_id=current_user.id, type_='Borrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe])
                    db.session.add(action)
        else:  # Create new borrow
            borrow = User_Rec(user_id=current_user.id, recipe_id=recipe_id, borrowed=True,
                              borrowed_dates={'Borrowed': [datetime.utcnow().strftime('%Y-%m-%d-%H-%M')], 'Unborrowed': []})
            flash(f"{recipe.title} borrowed!", 'success')
            action = Actions(user_id=current_user.id, type_='Borrow', recipe_ids=[recipe_id],
                             date_created=datetime.utcnow(), titles=[recipe.title])
            db.session.add(action)
            db.session.add(borrow)
        db.session.commit()
    return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))


@recipes.route('/publify/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def publify_recipe(recipe_id):
    recipe = Recipes.query.filter_by(id=recipe_id).first()
    # credit = current_user.credit  # todo public
    public = Recipes(user_id=current_user.id, title=recipe.title, quantity=recipe.quantity, notes=recipe.notes,
                     link=recipe.link, recipe_type=recipe.recipe_type, recipe_genre=recipe.recipe_genre,
                     picture=recipe.picture, servings=recipe.servings, originator=current_user.id)
    db.session.add(public)
    db.session.commit()
    return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))


# ######################################### functions, not views #################################################


@login_required
@recipes.route('/recipes/<int:recipe_id>/delete', methods=['POST'])
def delete_recipe(recipe_id):
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only change your own recipes
        abort(403)
        return redirect(url_for('recipes.recipes_page'))
    if recipe.title in current_user.harmony_preferences['recommended']:  # If delete recipe in recommended
        temp = {key: value for key, value in current_user.harmony_preferences.items()}
        temp['recommended'] = {}  # Reset recipe tool recommendations
        temp['possible'] = 0
        current_user.harmony_preferences = temp
    for rec in User_Rec.query.filter_by(recipe_id=recipe.id).all():
        db.session.delete(rec)
        pass
    db.session.delete(recipe)
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
def change_to_borrow():  # JavaScript way of adding to menu without reload  # todo public recipes
    recipe_id = int(request.form['recipe_id'])
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        title = recipe.title
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
        date = datetime.utcnow().strftime('%Y-%m-%d-%H-%M')
        recipe.borrowed_dates['Borrowed'].append(date) if recipe.borrowed else recipe.borrowed_dates['Unborrowed'].append(date)
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
    dictionary = current_user.harmony_preferences.copy()  # todo move to utils
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
