import itertools
import json
import string
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, abort, Blueprint, session
from flask_login import current_user, login_required
from GroceryHero import db
from GroceryHero.Main.utils import update_grocery_list, get_harmony_settings, rem_trail_zero
from GroceryHero.Modeling.svd import recipe_svd
from GroceryHero.Recipes.forms import RecipeForm, RecipeLinkForm, UploadRecipeImage, SvdForm
from GroceryHero.Recipes.utils import parse_ingredients, generate_feed_contents, get_friends, remove_menu_items, \
    recipe_stack_w_args, update_user_preferences, load_harmonyform, load_quantityform, paginate_sort
from GroceryHero.Users.forms import HarmonyForm
from GroceryHero.Users.utils import save_picture, Colors
from GroceryHero.models import Recipes, User, Followers, Actions, User_Rec
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode

recipes = Blueprint('recipes', __name__)


@login_required
@recipes.route('/recipes', methods=['GET', 'POST'])
@recipes.route('/recipes/<string:view>', methods=['GET', 'POST'])
def recipes_page(view='self'):
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    followees, all_friends = get_friends(current_user)
    possible, recommended, form, about, colors, friends, title = 0, None, HarmonyForm(), True, Colors.rec_colors, None, 'Recipes'
    search, page, sort, types, friend = search, page, sort, types, friend_choice = get_requests(all_friends)
    per = 100 if view != 'friends' else 50
    recipe_list, count, in_menu, borrows, recipe_ids = paginate_sort(friend_choice=friend_choice,
                                                                     search=search, page=page, sort=sort, type_=types,
                                                                     view=view, per=per)
    cards = recipe_list.items
    # friend is [id] unless one wasn't chosen, then it is just the whole friend dict
    if friend and (friend != all_friends):  # If a friend choice was made
        followee = Followers.query.filter_by(user_id=current_user.id, follow_id=friend[0]).first()
        if followee is None or followee.status != 1:  # Don't allow looking at recipes from people you don't follow
            return redirect(url_for('recipes.recipes_page', view='self'))
    if view != 'friends':
        in_menu = [r.title for r in in_menu] if in_menu is not None else []
        about = None if current_user.pro else True
        preferences = get_harmony_settings(current_user.harmony_preferences)
        recipe_hist = [[x.title for x in Recipes.query.filter(Recipes.id.in_(sublist)).all()] for sublist in
                       current_user.history]
        excludes = int(current_user.harmony_preferences['history'])
        recipe_ex = [item for sublist in recipe_hist[:excludes] for item in sublist]
        if request.method == "GET":
            form, recommended, recipe_ex, possible = load_harmonyform(current_user, form, in_menu, recipe_list.items,
                                                                      recipe_ex)
        if request.method == "POST":
            if form.validate_on_submit():  # Harmony or search button was pressed
                harmony_recipes = Recipes.query.filter_by(author=current_user).order_by(Recipes.title.asc()).all()  # todo include borrowed recipes
                num_in_menu = Recipes.query.filter_by(author=current_user, in_menu=True).count()
                form.groups.data = form.groups.data if (num_in_menu > 0) else 2  # Can't harmonize groups of 1
                recommended, possible = recipe_stack_w_args(harmony_recipes, preferences, form, in_menu, recipe_ex,
                                                            recipe_hist)
                recommended = remove_menu_items(in_menu, recommended)
                update_user_preferences(current_user, form, recommended, possible)
                form, recommended, _, possible = load_harmonyform(current_user, form, in_menu, harmony_recipes, recipe_ex)
    else:  # Friend recipes
        about, title, recipe_ids, view, friends = None, 'Friend Recipes', None, 'friends', True
    return render_template('recipes.html', title=title, cards=cards, sidebar=True, colors=colors,
                           borrows=borrows, count=count, friend_dict=all_friends, recipe_list=recipe_list,
                           recipe_ids=recipe_ids, friend=friend, about=about, combos=possible,
                           all_friends=all_friends, friends=friends,
                           recommended=recommended, form=form, page=page, sort=sort, types=types, view=view)


@login_required
@recipes.route('/public_recipes', methods=['GET', 'POST'])
def public_recipes():  # view for public may be redundant
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    colors, rankings = Colors.rec_colors, {}
    followees, all_friends = get_friends(current_user)
    search, page, sort, types, friend_choice = get_requests(all_friends)
    recipe_list, count, _, borrows, _ = paginate_sort(page=page, sort=sort, type_=types, search=search, view='public',
                                                      friend_choice=all_friends)
    cards = recipe_list.items
    form = SvdForm()
    # print(sorted([[x.trend_index, x.title] for x in Recipes.query.all()], key=lambda y: y[0], reverse=True))
    if request.method == 'POST':
        if form.validate_on_submit() and current_user.history:
            types = form.type_.data
            u_id = current_user.id
            all_users = User.query.all()
            rankings = recipe_svd(all_users)[u_id]
            rankings = [[x[0], round(x[1] ** (1 / 4) * 5, 2)] for x in rankings if
                        (x[0] is not None) and (x[0].user_id != u_id) and (x[0].id not in borrows)]
            rankings = [x for x in rankings if ((x[0].recipe_type == types) and
                                                (x[0].public or x[0].user_id in all_friends.keys()))][:5] \
                if types != 'all' else rankings[:5]  # Filter types and viewing privileges
    elif not current_user.history:
        flash('You must clear your menu at least once so the algorithm knows what foods you like', 'info')
    template = 'recipes_public.html'

    return render_template(template, title='Public Recipes', cards=cards, sidebar=True, colors=colors,
                           borrows=borrows, count=count, form=form,
                           recipe_list=recipe_list, page=page, sort=sort, types=types, view='public',
                           friend_dict=friend_choice, all_friends=friend_choice, public=True, rankings=rankings)


def get_requests(all_friends):
    search, page, sort, types, friend = request.form.get('search', None), request.args.get('page', 1, type=int), \
                                        request.args.get('sort', 'none'), request.args.get('types', 'all'), \
                                        request.args.get('friend', None, type=int)
    search = search if search not in ['Recipe Options', ''] else None
    sort = sort if sort in ['hot', 'borrow', 'date', 'eaten', 'alpha'] else 'none'
    types = types if types in ['all', 'Breakfast', 'Lunch', 'Dinner', 'Snack', 'Dessert', 'Other'] else 'all'
    friend_choice = list(all_friends.keys()) if friend is None else [friend]
    return search, page, sort, types, friend_choice


@login_required
@recipes.route('/friend_feed', methods=['GET', 'POST'])
def friend_feed():
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    colors = Colors.act_colors
    cards, friend_dict, friend_acts, page, count = [], {}, [], 1, 0
    friend = request.args.get('friend', None, type=int)
    all_followees = [x.follow_id for x in Followers.query.filter_by(user_id=current_user.id).all() if x.status == 1]
    followees = all_followees if friend is None else [friend]
    if followees and followees[0] not in all_followees:
        return redirect(url_for('recipes.friend_feed'))
    if followees:
        friend_dict = {id_: User.query.filter_by(id=id_).first() for id_ in all_followees}
        page = request.args.get('page', 1, type=int)
        friend_acts = Actions.query.filter(Actions.user_id.in_(followees)) \
            .order_by(Actions.date_created.desc()).paginate(page=page, per_page=10)
        count = len(friend_acts.items)
        cards = generate_feed_contents(friend_acts.items)
    return render_template('friend_feed.html', cards=cards, title='Friend Feed', sidebar=True,
                           colors=colors, friend_dict=friend_dict, all_friends=friend_dict, count=count,
                           friend_acts=friend_acts, friend=friend, page=page, friends=True, feed=True)


@login_required
@recipes.route('/recipes/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_single(recipe_id):  # TODO Minting recipe must be public
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    recipe_post = Recipes.query.get_or_404(recipe_id)
    author_id = recipe_post.author.id
    if author_id != current_user.id:
        following = Followers.query.filter_by(user_id=author_id, follow_id=current_user.id).first()
        status = following.getStatus() if following is not None else 'None'
        if (not recipe_post.public) and (status != 1):  # User is trying to look at nonpublic recipe (not friend either)
            return redirect(url_for('recipes.recipes_page', view='public'))
    else:
        status = 'Followed'
    form = UploadRecipeImage()
    quantity = {ingredient: [rem_trail_zero(recipe_post.quantity[ingredient][0]), recipe_post.quantity[ingredient][1]]
                for ingredient in recipe_post.quantity}  # todo is this still necessary?
    recipe_post.quantity = quantity
    url = recipe_post.picture
    url = url if url is not None else False  # todo might not be necessary
    # eaten and borrowed by others
    others_eaten = sum(x.times_eaten for x in User_Rec.query.filter_by(recipe_id=recipe_id).all())
    others_borrowed = sum(1 for x in User_Rec.query.filter_by(recipe_id=recipe_id).all() if x.borrowed)
    other_downloaded = sum(1 for x in User_Rec.query.filter_by(recipe_id=recipe_id).all() if x.downloaded)
    borrowed = True

    if recipe_post.author != current_user:
        borrow = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
        borrowed = False if borrow is None else borrow.borrowed

    if request.method == 'POST':  # Download recipe  # todo mint recipe
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = save_picture(form.picture.data, filepath='static/recipe_pics')
                recipe_post.picture = picture_file
                db.session.commit()
                flash('Your image has been uploaded!', 'success')
            return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
        elif recipe_post.author != current_user:  # POST on recipe single borrows if not same user
            return redirect(url_for('recipes.recipe_borrow', recipe_id=recipe_id))
    return render_template('recipe.html', title=recipe_post.title, recipe=recipe_post, recipe_single=True, sidebar=True,
                           url=url, form=form, others_eaten=others_eaten, others_borrowed=others_borrowed,
                           other_downloaded=other_downloaded, borrowed=borrowed, status=status)


@login_required
@recipes.route('/recipes/new', methods=['GET', 'POST'])
def new_recipe():  # Giving recipe's title, ingredient list, instructions and etc
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    if len(current_user.recipes) > 80:  # User recipe limit
        return redirect(url_for('main.account'))
    form = RecipeForm()
    if form.validate_on_submit():  # Send data to quantity page
        ingredients = [string.capwords(x.strip()) for x in form.content.data.split(',') if x.strip() != '']
        ingredients = {ingredient: [1, 'Unit'] for ingredient in ingredients}
        session['recipe'] = {'title': string.capwords(form.title.data), 'quantity': ingredients,  # Dict(ing:[unit,typ])
                             'notes': form.notes.data, 'type': form.type_.data, 'public': form.public.data}
        return redirect(url_for('recipes.new_recipe_quantity'))
    return render_template('create_recipe.html', title='New Recipe', form=form, legend='Recipe Details', link=True)


@login_required
@recipes.route('/recipes/new/quantity', methods=['GET', 'POST'])
def new_recipe_quantity():  # Show default/loaded ingredient quantity and measurement info, add to db on submit
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    recipe = session['recipe']  # {RecipeName: string, Quantity: {ingredient: [value,type]}}
    form = load_quantityform(recipe)
    if form.validate_on_submit():  # form.ingredient_forms.data- List(Ingredient_form(Dict())
        quantity = [data['ingredient_quantity'] for data in form.ingredient_forms.data]
        measure = [data['ingredient_type'] for data in form.ingredient_forms.data]
        formatted = {ingredient: [Q, M] for ingredient, Q, M in zip(form.ingredients, quantity, measure)}

        pic_fn = save_picture(recipe.get('im_path', None), 'static/recipe_pics', download=True)
        pic_fn = pic_fn if pic_fn is not None else 'default.png'
        public = False if recipe.get('public') == 'False' else True
        recipe = Recipes(title=(recipe['title']), quantity=formatted, user_id=current_user.id,
                         notes=recipe['notes'], recipe_type=recipe['type'], link=recipe.get('link', ''),
                         picture=pic_fn, public=public, credit=False)
        db.session.add(recipe)
        db.session.commit()
        recipe.originator = recipe.id
        action = Actions(user_id=current_user.id, type_='Add', recipe_ids=[recipe.id], date_created=datetime.utcnow(),
                         titles=[recipe.title])
        db.session.add(action)
        db.session.commit()
        flash('Your recipe has been created!', 'success')
        return redirect(url_for('recipes.recipes_page'))
    return render_template('recipe_quantity.html', title='New Recipe', form=form, legend='Recipe Ingredients',
                           recipe=recipe)


@login_required
@recipes.route('/recipes/link', methods=['GET', 'POST'])
def recipe_from_link():  # page where user enters url
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
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
                                 'measures': quantity, 'link': form.link.data if len(form.link.data) <= 64 else '',
                                 'im_path': im_path}
        return redirect(url_for('recipes.new_recipe_link'))  # todo change link string limit
    return render_template('recipe_link.html', title='New Recipe', legend='Recipe From Link', form=form,
                           recipe_link=True, sidebar=True)


@login_required
@recipes.route('/recipes/new_link', methods=['GET', 'POST'])
def new_recipe_link():  # Filling out the form data from link page
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    form = RecipeForm()
    if request.method == 'GET':
        if len(current_user.recipes) > 75:  # User recipe limit
            return redirect(url_for('main.account'))
        recipe = session['recipe_raw']
        form.title.data = recipe['title']
        form.content.data = ', '.join([x.replace(',', '') for x in recipe['ingredients']])  # todo not necessary?
        form.notes.data = recipe['notes']
    if form.validate_on_submit():  # Send data to quantity page
        ingredients = [string.capwords(x.strip()) for x in form.content.data.split(',') if x.strip() != '']
        # ings = {ing: session['recipe_raw']['measures'][i] for i, ing in enumerate(ingredients)}
        ings = {}  # todo dictionary comp
        for i, ing in enumerate(ingredients):  # session['recipe_raw']['ingredients']):  #
            # todo figure out how to link quantity with ingredients, despite deletion and modification
            ings[ing] = session['recipe_raw']['measures'][i]  # except IndexError: ings[ing] = [1, 'Unit']
        session['recipe'] = {'title': string.capwords(form.title.data), 'quantity': ings,
                             'notes': form.notes.data, 'type': form.type_.data, 'link': session['recipe_raw']['link'],
                             'im_path': session['recipe_raw']['im_path'], 'originator': None}
        return redirect(url_for('recipes.new_recipe_quantity'))
    return render_template('create_recipe.html', title='Recipe Details', form=form, legend='Recipe Details')


@login_required
@recipes.route('/recipes/<int:recipe_id>/update', methods=['GET', 'POST'])
def update_recipe(recipe_id):  # Update recipe attributes
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:  # You can only update your own recipes
        abort(403)
    form = RecipeForm()  # add public loaded
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
    return render_template('create_recipe.html', title='Update Recipe Details', form=form, legend='Update Recipe Details')


@login_required
@recipes.route('/recipes/<int:recipe_id>/update_quantity', methods=['GET', 'POST'])
def update_recipe_quantity(recipe_id):  # Update recipe quantity/measurement
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    rec = Recipes.query.get_or_404(recipe_id)
    if rec.author != current_user:  # You can only update your own recipes
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
@recipes.route('/recipes/<int:recipe_id>/download', methods=['GET', 'POST'])  # Makes a copy of someone else's recipe
def recipe_download(recipe_id):
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    all_recipes = Recipes.query.filter_by(author=current_user).all()
    recipe = Recipes.query.filter_by(id=recipe_id).first()
    for r in all_recipes:  # Make sure user doesn't already have the recipe
        if recipe == r:
            flash(f'Recipe {recipe.title} already in recipe library', 'danger')
            return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
    original_id = recipe.originator  # Original recipe ID
    original_id = original_id if original_id != recipe_id else recipe_id  # If downloading original recipe, take its ID
    new_rec = Recipes(title=recipe.title, quantity=recipe.quantity, notes=recipe.notes, user_id=current_user.id,
                      link=recipe.link, recipe_type=recipe.recipe_type, recipe_genre=recipe.recipe_genre,
                      picture=recipe.picture, servings=recipe.servings, originator=original_id,
                      price=recipe.price, options=recipe.options)
    db.session.add(new_rec)
    db.session.commit()
    user_rec = User_Rec.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    if user_rec is None:  # User has no record with recipe they are downloading
        user_rec = User_Rec(recipe_id=recipe_id, user_id=current_user.id, downloaded=True)
        user_rec.downloaded_dates = [datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')]
        db.session.add(user_rec)
        action = Actions(user_id=current_user.id, type_='Download', recipe_ids=[new_rec.id],
                         date_created=datetime.utcnow(), titles=[new_rec.title])
        db.session.add(action)
    else:
        if not user_rec.downloaded:  # user hasn't downloaded this recipe before
            action = Actions(user_id=current_user.id, type_='Download', recipe_ids=[new_rec.id],
                             date_created=datetime.utcnow(), titles=[new_rec.title])
            db.session.add(action)
            user_rec.downloaded = True
        user_rec.downloaded_dates.append(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    db.session.commit()
    flash(f'{new_rec.title} added to your library!', 'success')
    return redirect(url_for('recipes.recipe_single', recipe_id=new_rec.id))


@login_required
@recipes.route('/borrow/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_borrow(recipe_id):  # From single page to borrowing the recipe
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.user_id == current_user.id:
        return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))
    else:
        borrowed = User_Rec.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if borrowed is not None:  # If user currently has history with recipe  # todo move logic to utils
            if borrowed.borrowed:
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = False, False, False
                borrowed.borrowed_dates['Unborrowed'].append(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
                flash(f"You have returned {recipe.title}", 'info')
                if len(borrowed.borrowed_dates['Unborrowed']) == 1:  # First time unborrowing
                    action = Actions(user_id=current_user.id, type_='Unborrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe.title])
                    db.session.add(action)
            else:  # Not currently borrowed
                borrowed.borrowed, borrowed.in_menu, borrowed.eaten = True, False, False
                borrowed.borrowed_dates['Borrowed'].append(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
                flash(f"{recipe.title} borrowed!", 'success')
                if len(borrowed.borrowed_dates['Borrowed']) == 1:  # First time borrowing
                    action = Actions(user_id=current_user.id, type_='Borrow', recipe_ids=[recipe_id],
                                     date_created=datetime.utcnow(), titles=[recipe])
                    db.session.add(action)
        else:  # Create new borrow
            borrow = User_Rec(user_id=current_user.id, recipe_id=recipe_id, borrowed=True,
                              borrowed_dates={'Borrowed': [datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')],
                                              'Unborrowed': []})
            flash(f"{recipe.title} borrowed!", 'success')
            action = Actions(user_id=current_user.id, type_='Borrow', recipe_ids=[recipe_id],
                             date_created=datetime.utcnow(), titles=[recipe.title])
            db.session.add(action)
            db.session.add(borrow)
        db.session.commit()
    return redirect(url_for('recipes.recipe_single', recipe_id=recipe_id))


# ######################################### functions, not views #################################################


@login_required
@recipes.route('/recipes/<int:recipe_id>/delete', methods=['POST'])
def delete_recipe(recipe_id):
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
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
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
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
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
    recipe_id = int(request.form['recipe_id'])
    recipe = Recipes.query.get_or_404(recipe_id)
    if recipe.author != current_user:
        title = recipe.title
        recipe = User_Rec.query.get([current_user.id, recipe_id])
        if recipe is None:  # If user hasn't borrowed this recipe before make new entry
            user_id = current_user.id
            borrow = User_Rec(user_id=user_id, recipe_id=recipe_id, borrowed=True,
                              borrowed_dates={'Borrowed': [datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')],
                                              'Unborrowed': []})
            action = Actions(user_id=user_id, type_='Borrow', recipe_ids=[recipe_id], date_created=datetime.utcnow(),
                             titles=[title])
            db.session.add(action)
            db.session.add(borrow)
            db.session.commit()
            return json.dumps({'result': 'success'})
        # Person has borrowed this recipe before (entry exists)
        recipe.borrowed = not recipe.borrowed
        date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        recipe.borrowed_dates['Borrowed'].append(date) if recipe.borrowed else recipe.borrowed_dates[
            'Unborrowed'].append(date)
        recipe.in_menu = False
        recipe.eaten = False
    db.session.commit()
    return json.dumps({'result': 'success'})


@recipes.route('/recipes/<int:recipe_id>/add_menu', methods=['GET', 'POST'])  # ??REQUIRES 'GET'
@login_required
def add_to_menu(recipe_id):  # Adding from RHT recommendations
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
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
    if not current_user.is_authenticated:
        return redirect(url_for('main.landing'))
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

# elif recipe_post.user_id == current_user.id:
#     title = recipe_post.title
#     recipes = json.dumps({title: [recipe_post.quantity, recipe_post.notes]}, indent=2)
#     return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
#                                                              f"attachment; filename={title}.txt"})


"""
import string
from GroceryHero.Recipes.utils import parse_ingredients
from GroceryHero.Users.utils import save_picture
from recipe_scrapers import scrape_me, WebsiteNotImplementedError, NoSchemaFoundInWildMode
from GroceryHero.models import Recipes
from GroceryHero import db, create_app
db.app = create_app()


def recipe_from_link(link):  # page where user enters url
    try:
        scraper = scrape_me(link)
    except WebsiteNotImplementedError:
        try:
            scraper = scrape_me(link, wild_mode=True)
        except NoSchemaFoundInWildMode:
            return {}
    ingredients = [x.lower() for x in scraper.ingredients()]
    ings, quantity = parse_ingredients(ingredients)
    ings = [string.capwords(x.strip()) for x in ings if x.strip() != '']
    im_path = scraper.image()
    quantity = {ingredient: [Q, M] for ingredient, (Q, M) in zip(ings, quantity)}
    # servings = scraper.yields()
    prep_time = scraper.total_time()
    recipe_dict = {'title': scraper.title(), 'notes': scraper.instructions(),
                   'quantity': quantity, 'link': link, 'im_path': im_path, 'prep_time': prep_time}
    return recipe_dict


def zuck(recipe):  # If recipe is not empty
    title = recipe['title']
    quantity = recipe['quantity']
    notes = recipe['notes']
    prep_time = float(recipe['prep_time']) if recipe['prep_time'] != 0 else None
    prep_time = {'total': int(prep_time)} if ((prep_time is not None) and prep_time.is_integer()) else prep_time
    rtype = 'Dinner'
    link = recipe.get('link', '')
    pic_fn = save_picture(recipe.get('im_path', None), 'static/recipe_pics', download=True)
    pic_fn = pic_fn if pic_fn is not None else 'default.png'
    recipe = Recipes(title=title, quantity=quantity, user_id=14,
                     notes=notes, recipe_type=rtype, link=link,
                     picture=pic_fn, public=True, prep_time=prep_time, credit=False)
    return recipe


def zuckRecipes(start=6_663, end=26_894):
    site = 'https://www.allrecipes.com/recipe/'
    start = 13884
    for i in range(start, end):
        try:
            recipe = recipe_from_link(site+str(i)+'/')  # Returns dict
            if recipe:  #
                recipe = zuck(recipe)
                db.session.add(recipe)
            else:
                print(i)
            if (i % 10) == 0:
                db.session.commit()
                # recipe.originator = recipe.id
                # db.session.commit()
        except Exception as e:
            print(e)

with db.app.app_context():
    zuckRecipes()
    
    
for recipe in db.session.query(Recipes).all():
    recipe.public = True
db.session.commit()

"""