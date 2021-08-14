import string

from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from GroceryHero import db
from GroceryHero.Main.utils import update_grocery_list
from GroceryHero.models import Aisles, Recipes
from GroceryHero.Aisles.forms import AisleForm, AisleBarForm

aisles = Blueprint('aisles', __name__)


@aisles.route('/aisles', methods=['GET', 'POST'])
def aisles_page():
    aisle_list = []
    form = AisleBarForm()
    form.unadded.choices = zip(['All Items Sorted!'], ['All Items Sorted!'])
    if current_user.is_authenticated:
        if request.method == 'POST':
            if form.aisles.data != '' and form.aisles.data != 'No Aisles Yet' and form.unadded.data != 'All Items ' \
                                                                                                       'Sorted!':
                aisle = Aisles.query.filter_by(title=form.aisles.data).first()
                content = aisle.content.split(', ')
                if isinstance(form.unadded.data, list):
                    for item in form.unadded.data:
                        content.append(item)
                else:
                    content.append(form.unadded.data)
                aisle.content = ', '.join(sorted(content))
                db.session.commit()
            else:
                return redirect(url_for('aisles.aisles_page'))
        aisle_list = Aisles.query.filter_by(author=current_user).order_by(Aisles.order).all()
        aisle_list = [a for a in aisle_list if a.order > 0]+[a for a in aisle_list if a.order < 1]
        aisle_ingredients = set([item for sublist in aisle_list for item in sublist.content.split(', ')])
        if len(aisle_list) > 0:
            form.aisles.choices = [aisle.title for aisle in aisle_list]
        ingredients = [set(recipe.quantity.keys()) for recipe in Recipes.query.filter_by(author=current_user).all()]
        choices = sorted(set([item for sublist in ingredients for item in sublist if item not in aisle_ingredients]))
        form.unadded.choices = [x for x in zip([0]+choices, ['-- select options (clt+click) --']+choices)]
        if len(form.unadded.choices) < 1:
            form.unadded.choices = zip(['All Items Sorted!'], ['All Items Sorted!'])
    return render_template('aisles.html', aisles=aisle_list, title='Aisles', sidebar=True, form=form, aisle=True)


@aisles.route('/aisles/new', methods=['GET', 'POST'])
@login_required
def new_aisle():
    form = AisleForm()
    if form.validate_on_submit():
        store = form.store.data if form.store.data != '' else None
        order = int(form.order.data) if form.order.data != '' else None
        form = Aisles(title=string.capwords(form.title.data.strip()), order=order,
                      content=', '.join([word.strip().capitalize() for word in form.content.data.split(',')]),
                      store=store, author=current_user)
        db.session.add(form)
        db.session.commit()
        update_grocery_list(current_user)
        flash('Your aisle has been created!', 'success')
        return redirect(url_for('aisles.aisles_page'))
    return render_template('create_aisle.html', title='New Aisle', form=form, legend='New Aisle')


@aisles.route('/aisles/<int:aisle_id>')
def aisle_single(aisle_id):
    aisle_post = Aisles.query.get_or_404(aisle_id)
    return render_template('aisle.html', title=aisle_post.title, aisle=aisle_post)


@aisles.route('/aisles/<int:aisle_id>/update', methods=['GET', 'POST'])
@login_required
def update_aisle(aisle_id):
    aisle = Aisles.query.get_or_404(aisle_id)
    if aisle.author != current_user:  # You can only update your own aisles
        abort(403)
    form = AisleForm()
    if form.validate_on_submit():
        aisle.title = string.capwords(form.title.data)
        aisle.content = ', '.join([string.capwords(word.strip()) for word in form.content.data.split(',')])
        aisle.store = ' '.join([word.strip().capitalize() for word in form.store.data.split(' ')])
        aisle.order = int(form.order.data) if form.order.data != '' else 0
        db.session.commit()  # Don't need to do db.add since we are changing an existing entry
        update_grocery_list(current_user)
        flash('Your aisle has been updated!', 'success')
        return redirect(url_for('aisles.aisle_single', aisle_id=aisle.id))
    elif request.method == 'GET':
        form.order.default = aisle.order
        form.process()
        form.title.data = aisle.title
        form.content.data = aisle.content
        form.store.data = aisle.store
    return render_template('create_aisle.html', title='Update Aisle', form=form, legend='Update Aisle')


@aisles.route('/aisles/<int:aisle_id>/delete', methods=['POST'])
@login_required
def delete_aisle(aisle_id):
    aisle = Aisles.query.get_or_404(aisle_id)
    if aisle.author != current_user:  # You can only update your own aisles
        abort(403)
    db.session.delete(aisle)
    db.session.commit()
    update_grocery_list(current_user)
    flash('Your aisle has been deleted!', 'success')
    return redirect(url_for('aisles.aisles_page'))

