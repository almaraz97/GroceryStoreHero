from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from werkzeug.routing import ValidationError
from wtforms import StringField, SubmitField, TextAreaField, SelectField, FieldList, FormField, ValidationError, \
    FileField
from wtforms.validators import InputRequired, DataRequired, URL, NoneOf
from GroceryHero.Recipes.utils import Measurements


class RecipeForm(FlaskForm):
    title = StringField('Recipe Name', validators=[DataRequired(),
                                                   NoneOf(values=['<', '>'], message=" '>' and '<' symbols not allowed")])
    content = TextAreaField('Ingredients (separate with commas)', validators=[DataRequired()])
    type_ = SelectField('Type', choices=[(x, x) for x in ['Breakfast', 'Lunch', 'Dinner', 'Dessert', 'Snack', 'Other']],
                        default='Dinner')
    notes = TextAreaField('Notes/Instructions (optional)')
    submit = SubmitField('Next')


class RecipeLinkForm(FlaskForm):
    link = StringField('Recipe Link', validators=[DataRequired(), URL()])
    submit = SubmitField('Next')


class QuantityForm(FlaskForm):
    ingredient_quantity = StringField('Quantity', default=1.0, validators=[InputRequired()])  # , dec_frac()
    ingredient_type = SelectField("Measurement", choices=[(x, x) for x in Measurements.Measures], default='Unit')

    @staticmethod
    def validate_ingredient_quantity(self, field):
        try:
            float(field.data)
        except ValueError:
            try:  # May be correct format for division
                if '/' not in field.data or field.data.count('/') > 1:  # No division or too many
                    raise ValidationError('Enter a number or a fraction')
                else:  # See if other values are floats
                    temp = [float(x) for x in field.data.split('/')]
            except ValueError:
                raise ValidationError('Enter a number or a fraction')


class FullQuantityForm(FlaskForm):
    ingredients = []
    ingredient_forms = FieldList(FormField(QuantityForm), min_entries=1)
    notes = ''
    submit = SubmitField('Submit')


class UploadRecipeImage(FlaskForm):
    picture = FileField('Update Recipe Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Upload')
