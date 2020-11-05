import itertools

from flask import render_template, url_for, flash, redirect, request, Blueprint, Response
from flask_login import login_user, current_user, logout_user, login_required
from GroceryHero import db, bcrypt
from GroceryHero.models import User, Recipes, Aisles
from GroceryHero.Users.forms import (RegistrationForm, LoginForm, UpdateAccountForm, DeleteAccountForm,
                                     RequestResetForm, ResetPasswordForm, AdvancedHarmonyForm)
from GroceryHero.Main.forms import ImportForm
from GroceryHero.Users.utils import save_picture, send_reset_email, import_files, update_harmony_preferences, \
    load_harmony_form
from GroceryHero.Main.utils import get_harmony_settings, show_harmony_weights
import json

users = Blueprint('users', __name__)


@users.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.password = hashed_password
        user.harmony_preferences = {'excludes': [], 'similarity': 50, 'groups': 3, 'possible': 0, 'recommended': {},
                                    'rec_limit': 3, 'tastes': {}, 'ingredient_weights': {}, 'sticky_weights': {},
                                    'recipe_ids': {}, 'menu_weight': 1, 'algorithm': 'Balanced'}
        # todo create default recipes here
        db.session.add(user)
        db.session.commit()
        flash(f'Your account has been created. You can now log in!', 'success')
        return redirect(url_for("users.login"))
    return render_template('register.html', title='Register', form=form)


@users.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash(f"Login Unsuccessful. Please check email or password", 'danger')
    return render_template('login.html', title='Login', form=form)


@users.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    form2 = ImportForm()
    form3 = AdvancedHarmonyForm()
    form4 = DeleteAccountForm()
    # Shows user their previous settings
    preferences = get_harmony_settings(current_user.harmony_preferences)
    ing_weights, tastes, sticky = show_harmony_weights(current_user, preferences)
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated', 'success')
        return redirect(url_for('users.account'))
    if form2.import_recipes_button.data or form2.import_aisles_button.data:
        import_type = 'recipes' if form2.import_recipes_button.data else 'aisles'
        import_files(form2.file_name.data, import_type)
        return redirect(url_for('users.account'))
    if form3.is_submitted():
        update_harmony_preferences(form3, current_user)
        db.session.commit()
        flash('Your settings have been updated', 'success')
        return redirect(url_for('users.account'))
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form3 = load_harmony_form(AdvancedHarmonyForm(), current_user)
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form, form2=form2,
                           form3=form3, form4=form4, sidebar=True, account=True, ing_weights=ing_weights, tastes=tastes,
                           sticky_weights=sticky)


@users.route('/delete_account/<int:token>', methods=['GET', 'POST'])
@login_required
def delete_account(token):
    if token:
        recipes = Recipes.query.filter_by(author=current_user).all()
        for recipe in recipes:
            db.session.delete(recipe)
        aisles = Aisles.query.filter_by(author=current_user).all()
        for aisle in aisles:
            db.session.delete(aisle)
        db.session.delete(current_user)
        db.session.commit()
        flash('Your account has been deleted!', 'success')
        return redirect(url_for('main.home'))


@users.route('/account/download', methods=['GET', 'POST'])
def export():
    if current_user.is_authenticated:
        if request.form['export'] == 'Recipes':
            recipes = Recipes.query.filter_by(author=current_user).all()
            recipes = json.dumps({recipe.title: [recipe.quantity, recipe.notes] for recipe in recipes}, indent=2)
            return Response(recipes, mimetype="text/plain", headers={"Content-disposition":
                                                                     "attachment; filename=recipes.txt"})
        elif request.form['export'] == 'Aisles':
            aisles = Aisles.query.filter_by(author=current_user).all()
            aisles = json.dumps({aisle.title: [aisle.content, aisle.store] for aisle in aisles}, indent=2)
            return Response(aisles, mimetype="text/plain", headers={"Content-disposition":
                                                                    "attachment; filename=aisles.txt"})
    return redirect(url_for('users.account'))


@users.route('/reset_password', methods=['GET', 'POST'])
def reset_request():  # Sends user email to reset password
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@users.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):  # Where they reset password with active token
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for("users.login"))
    return render_template('reset_token.html', title='Reset Password', form=form)