from functools import wraps
from urllib.parse import urlencode
from authlib.integrations.base_client import OAuthError
from flask import current_app
from flask import render_template, url_for, flash, redirect, request, Blueprint, Response, session
from flask_login import login_user, current_user, logout_user, login_required
from GroceryHero import db
from GroceryHero.models import User, Recipes, Aisles, Followers, Actions, User_Rec, User_Act
from GroceryHero.Users.forms import UpdateAccountForm, DeleteAccountForm, AdvancedHarmonyForm, FriendForm
from GroceryHero.Main.forms import ImportForm
from GroceryHero.Users.utils import save_picture, import_files, update_harmony_preferences, load_harmony_form, \
    getRequestsFollowers
from GroceryHero.Main.utils import get_harmony_settings, show_harmony_weights, ensure_harmony_keys
import json

users = Blueprint('users', __name__)


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if len(current_user.recipes) >= 80:
        flash('You\'ve reached the maximum recipes without a membership. Borrow more or consider upgrading.', 'info')
    form = UpdateAccountForm()
    form2 = ImportForm()
    form3 = AdvancedHarmonyForm()
    form4 = DeleteAccountForm()
    form5 = FriendForm()
    # Shows user their previous settings
    preferences = get_harmony_settings(current_user.harmony_preferences)
    ing_weights, tastes, sticky = show_harmony_weights(current_user, preferences)
    requests, followers = getRequestsFollowers(current_user)
    # Update user info
    if form.validate_on_submit():  # Only on change
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated', 'success')
        return redirect(url_for('users.account'))
    # Importing
    if form2.import_recipes_button.data or form2.import_aisles_button.data:
        import_type = 'recipes' if form2.import_recipes_button.data else 'aisles'
        import_files(form2.file_name.data, import_type)
        return redirect(url_for('users.account'))
    # Update harmony
    if form3.validate_on_submit():
        update_harmony_preferences(form3, current_user)
        db.session.commit()
        flash('Your settings have been updated', 'success')
        return redirect(url_for('users.account'))
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form3 = load_harmony_form(AdvancedHarmonyForm(), current_user)
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form, form2=form2,form3=form3,
                           form4=form4, form5=form5, sidebar=True, account=True, ing_weights=ing_weights, tastes=tastes,
                           sticky_weights=sticky, requests=requests, followers=followers)


@users.route('/account/add_friend', methods=['GET', 'POST'])
@login_required
def request_friend():
    if len(current_user.recipes) >= 80:
        flash('You\'ve reached the maximum recipes without a membership. Borrow more or consider upgrading.', 'info')
    form = UpdateAccountForm()
    form2 = ImportForm()
    form3 = load_harmony_form(AdvancedHarmonyForm(), current_user)
    form4 = DeleteAccountForm()
    form5 = FriendForm()
    # Shows user their previous settings
    preferences = get_harmony_settings(current_user.harmony_preferences)
    ing_weights, tastes, sticky = show_harmony_weights(current_user, preferences)
    form.username.data = current_user.username
    form.email.data = current_user.email
    requests, followers = getRequestsFollowers(current_user)
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    if form5.validate_on_submit():
        email = form5.email.data.strip()  # Needed?
        followee = User.query.filter_by(email=email).first()
        follow_id = followee.id if followee is not None else None
        if follow_id is not None:  # Email exists in db
            follow = Followers.query.filter_by(user_id=current_user.id, follow_id=follow_id).first()
            if follow is None:  # Hasn't requested this person before
                follow = Followers(user_id=current_user.id, follow_id=follow_id, status=0)
                db.session.add(follow)
                db.session.commit()
            if follow.status == 1:
                flash('You already follow this user', 'success')
            else:  # Has requested before
                flash('Your request has been sent', 'info')
        return redirect(url_for('users.account'))
    return render_template('account.html', title='Account', image_file=image_file, form=form, form2=form2,form3=form3,
                           form4=form4, form5=form5, sidebar=True, account=True, ing_weights=ing_weights, tastes=tastes,
                           sticky_weights=sticky, requests=requests, followers=followers)


@users.route('/account/request/<int:f_id>', methods=['POST'])  # todo do I need to redirect back?
@login_required
def recipe_follow(f_id):
    # print(f_id)
    if f_id != 'none' and f_id != '':  # todo what happens to empty user?
        follow = Followers.query.filter_by(user_id=f_id, follow_id=current_user.id).first()
        if follow is None:
            follow = Followers(user_id=f_id, follow_id=current_user.id, status=0)
            db.session.add(follow)
            db.session.commit()
    return None


@users.route('/account/accept/<int:f_id>', methods=['GET', 'POST'])
@login_required
def accept_friend(f_id):
    follow = Followers.query.filter_by(user_id=f_id, follow_id=current_user.id).first()
    if follow is not None:
        follow.status = 1
        db.session.commit()
    return redirect(url_for('users.account'))


@users.route('/account/reject/<int:f_id>', methods=['GET', 'POST'])
@login_required
def reject_friend(f_id):
    follow = Followers.query.filter_by(user_id=f_id, follow_id=current_user.id).first()
    if follow is not None:
        db.session.delete(follow)
        db.session.commit()
    return redirect(url_for('users.account'))


@users.route('/account/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    form4 = DeleteAccountForm()
    # delete account
    if form4.validate_on_submit():
        for x in [Recipes, Aisles, Followers, Actions, User_Rec, User_Act]: #User_PubRec
            try:  # Deletes all user info from each table
                z = x.query.filter_by(author=current_user).all()
                for i in z:
                    db.session.delete(i)
            except Exception as e:
                print(e)
                z = x.query.filter_by(user_id=current_user.id).all()
                for i in z:
                    db.session.delete(i)
        db.session.delete(current_user)  # delete user
        db.session.commit()
        flash('Your account and everything associated has been deleted.', 'success')
        return redirect(url_for('main.home'))
    return redirect(url_for('users.account'))


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


# @users.route('/reset_password', methods=['GET', 'POST'])
# def reset_request():  # Sends user email to reset password
#     if current_user.is_authenticated:
#         return redirect(url_for('main.home'))
#     form = RequestResetForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         send_reset_email(user)
#         flash('An email has been sent with instructions to reset your password', 'info')
#         return redirect(url_for('users.login'))
#     return render_template('reset_request.html', title='Reset Password', form=form)


# @users.route('/reset_password/<token>', methods=['GET', 'POST'])
# def reset_token(token):  # Where they reset password with active token
#     if current_user.is_authenticated:
#         return redirect(url_for('main.home'))
#     user = User.verify_reset_token(token)
#     if user is None:
#         flash('That is an invalid or expired token', 'warning')
#         return redirect(url_for('users.reset_request'))
#     form = ResetPasswordForm()
#     if form.validate_on_submit():
#         hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#         user.password = hashed_password
#         db.session.commit()
#         flash(f'Your password has been updated! You are now able to log in', 'success')
#         return redirect(url_for("users.login"))
#     return render_template('reset_token.html', title='Reset Password', form=form)


# Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero # Auth Zero

def requires_auth(f): # Here we're using the /callback route.
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)
  return decorated


@users.route('/auth_login/callback')
def callback_handling():
    try:
        # Handles response from token endpoint
        current_app.auth0.authorize_access_token()
    except OAuthError:
        # flash(f"Login unsuccessful- email address was not provided and/or verified."
        #       f"Sign up here or sign in through another connection.", 'danger')
        return redirect(url_for('main.landing'))
    resp = current_app.auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect(url_for('users.auth_login'))


@users.route('/auth_login', methods=['GET', 'POST'])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if session.get('jwt_payload', False):  # User has been authenticated by auth0 and payload is in session
        email = session['jwt_payload'].get('email', False)
        if type(email) is str:
            email = email.lower()
        verified = session['jwt_payload'].get('email_verified', False)
        session['verify'] = verified
        session['email'] = email
        if email and verified:  # User email has been provided
            user = User.query.filter_by(email=email).first()
            if user is not None:  # User is in database
                login_user(user)
                next_page = request.args.get('next')
                ensure_harmony_keys(user)  # Make sure groceryList, extras and harmony_preferences JSON columns exist
                return redirect(next_page) if next_page else redirect(url_for('main.home'))
            else:  # User is not in database, register them
                name = session['jwt_payload'].get('given_name')
                name = session['jwt_payload'].get('nickname') if name is None else name
                name = session['jwt_payload'].get('name') if name is None else name
                username = name.strip() if name is not None else email.strip()
                user = User(email=email, username=username)
                picture_url = session['jwt_payload'].get('picture')
                if picture_url is not None:
                    try:
                        filename = save_picture(picture_url, filepath='static/profile_pics', download=True)
                    except Exception as e:  # Seems filename
                        print(e)
                        filename = None
                    if filename is not None:
                        user.picture = filename
                db.session.add(user)
                db.session.commit()
                ensure_harmony_keys(user)
                login_user(user)
                redirect(url_for('main.home'))
        else:
            return redirect(url_for('users.auth_logout'))
    return current_app.auth0.authorize_redirect(redirect_uri=current_app.auth0_urls['callback'])


@users.route('/auth_logout')
def auth_logout():
    if not session.get('verify', True):  # todo is this needed?
        flash("Email verification sent. Check your email to confirm you account.", 'info')
    if not session.get('email', False):
        flash(f"Login unsuccessful- an email address was not provided."
              f"Sign up manually or sign in through another connection.", 'danger')
    logout_user()
    session.clear()  # Clear session stored data
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('main.landing', _external=True), 'client_id': current_app.client_id}
    return redirect(current_app.auth0.api_base_url + '/v2/logout?' + urlencode(params))


@users.route('/privacy', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html', title='Privacy')


#   File "/home/alexa/GroceryStoreHero/GroceryHero/Users/routes.py", line 278, in auth_login
#     filename = save_picture(picture_url, filepath='static/profile_pics', download=True)
#   File "/home/alexa/GroceryStoreHero/GroceryHero/Users/utils.py", line 48, in save_picture
#     i.save(picture_path)
#   File "/home/alexa/.local/lib/python3.8/site-packages/PIL/Image.py", line 2133, in save
#     raise ValueError(f"unknown file extension: {ext}") from e
# ValueError: unknown file extension:
# [2021-01-02 21:08:43,708] ERROR in app: Exception on /auth_login [GET]
# Traceback (most recent call last):
#   File "/home/alexa/.local/lib/python3.8/site-packages/PIL/Image.py", line 2131, in save
#     format = EXTENSION[ext]
# KeyError: ''
