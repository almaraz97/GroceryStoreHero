from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, FloatField, FieldList, FormField, SelectMultipleField, StringField, \
    TextAreaField
from wtforms.validators import DataRequired
from GroceryHero.Recipes.forms import Measurements


class PantryBarForm(FlaskForm):
    name = SelectField("Name", choices=['No Shelves Yet'], default=['Select a Shelf'])
    content = SelectMultipleField("Ingredients", choices=['No Ingredients Yet'], default=['No Ingredients Yet'])
    ingredient_quantity = FloatField('Quantity', default=1.0, validators=[DataRequired()])
    ingredient_type = SelectField("Measurement", choices=Measurements.Measures, default='Unit')
    submit = SubmitField('Next')


class ShelfForm(FlaskForm):
    name = StringField('Shelf Name', validators=[DataRequired()])
    content = TextAreaField('Ingredients (separate with commas)', validators=[DataRequired()])
    submit = SubmitField('Next')


class QuantityForm(FlaskForm):
    ingredient_quantity = FloatField('Quantity', default=1.0, validators=[DataRequired()])
    ingredient_type = SelectField("Measurement", choices=Measurements.Measures, default='Unit')


class FullQuantityForm(FlaskForm):
    ingredients = []
    ingredient_forms = FieldList(FormField(QuantityForm), min_entries=1)
    submit = SubmitField('Submit')
