from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, FloatField, FieldList, FormField, SelectMultipleField, StringField, \
    TextAreaField
from wtforms.validators import InputRequired
from GroceryHero.Recipes.forms import Measurements as M


class PantryBarForm(FlaskForm):
    name = SelectField("Name", choices=['No Shelves Yet'], default=['Select a Shelf'])
    content = SelectMultipleField("Ingredients", validators=[InputRequired()])
    ingredient_quantity = FloatField('Quantity', default=1.0, validators=[InputRequired()])
    ingredient_type = SelectField("Measurement", choices=[(x, x) for x in M.Measures], default='Unit')
    add = SubmitField('Add')
    remove = SubmitField('Remove')


class ShelfForm(FlaskForm):
    name = StringField('Shelf Name', validators=[InputRequired()])
    content = TextAreaField('Ingredients (separate with commas)', validators=[InputRequired()])
    submit = SubmitField('Next')


class AddToShelfForm(FlaskForm):
    shelves = SelectField("Shelves", default='[<--Choose-->]')
    multi = SelectMultipleField('Recipe Ingredients')
    other = TextAreaField('Ingredients (separate with commas)', validators=[InputRequired()])
    submit = SubmitField('Next')


class QuantityForm(FlaskForm):
    ingredient_quantity = FloatField('Quantity', default=1.0, validators=[InputRequired()])
    ingredient_type = SelectField("Measurement", choices=M.Measures, default='Unit')


class FullQuantityForm(FlaskForm):
    ingredients = []
    ingredient_forms = FieldList(FormField(QuantityForm), min_entries=1)
    submit = SubmitField('Submit')


class DeleteShelfForm(FlaskForm):
    shelves = SelectMultipleField('Shelves')
    submit = SubmitField('Delete')