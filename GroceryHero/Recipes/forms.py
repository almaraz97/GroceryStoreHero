from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from werkzeug.routing import ValidationError
from wtforms import StringField, SubmitField, TextAreaField, SelectField, FieldList, FormField, ValidationError, \
    FileField, RadioField
from wtforms.validators import InputRequired, DataRequired, URL, NoneOf
from GroceryHero.Recipes.utils import Measurements


class RecipeForm(FlaskForm):
    title = StringField('Recipe Name', validators=[DataRequired(),
                                                   NoneOf(values=['<', '>'], message=" '>' and '<' symbols not allowed")])
    content = TextAreaField('Ingredients (separate with commas)', validators=[DataRequired()])
    type_ = SelectField('Type', choices=[(x, x) for x in ['Breakfast', 'Lunch', 'Dinner', 'Dessert', 'Snack', 'Other']],
                        default='Dinner')
    public = RadioField('Public', choices=[('True', 'True'), ('False', 'False')], default='True')
    notes = TextAreaField('Notes/Instructions (optional)')
    submit = SubmitField('Next')


class RecipeLinkForm(FlaskForm):
    link = StringField('Recipe Link', validators=[DataRequired(), URL()])
    submit = SubmitField('Next')


class QuantityForm(FlaskForm):
    ingredient_name = StringField('Ingredient', default='Default ingredient')  # For editing on quantity page
    ingredient_quantity = StringField('Quantity', default=1.0, validators=[InputRequired()])  # , dec_frac()
    ingredient_type = SelectField("Measurement", choices=[(x, x) for x in Measurements.Measures], default='Unit')
    ingredient_descriptor = StringField('Descriptor', default=1.0)  # For accompanying text

    @staticmethod
    def validate_ingredient_quantity(self, field):  # Make sure quantity is either a decimal or valid fraction
        try:
            float(field.data)
        except ValueError:
            try:  # May be correct format for division
                if '/' not in field.data or field.data.count('/') > 1:  # No division or too many division symbols
                    raise ValidationError('Enter a number or a fraction')
                else:  # See if other values are floats
                    temp = [float(x) for x in field.data.split('/')]
            except ValueError:
                raise ValidationError('Enter a number or a fraction')


class FullQuantityForm(FlaskForm):
    ingredients = []  # This should be editable todo is this being used?
    ingredient_forms = FieldList(FormField(QuantityForm), min_entries=1)
    notes = ''
    submit = SubmitField('Submit')


class UploadRecipeImage(FlaskForm):
    picture = FileField('Update Recipe Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Upload')


class SvdForm(FlaskForm):
    type_ = SelectField('Recipe Type', choices=[('all', 'All')]+[(x, x) for x in ['Breakfast', 'Lunch', 'Dinner', 'Dessert', 'Snack', 'Other']])
    submit = SubmitField('Find New Recipes')
