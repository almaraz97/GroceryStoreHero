from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired


class AisleForm(FlaskForm):
    title = StringField('Name', validators=[DataRequired()])
    content = TextAreaField('Ingredients (separate with commas)', validators=[DataRequired()])
    store = StringField('Store (optional)', validators=[])
    order = SelectField("Aisle Order- the way you go through the store (optional)",
                        choices=[('', '')]+[(str(x), str(x)) for x in range(1, 16)])
    submit = SubmitField('Submit')


class AisleBarForm(FlaskForm):
    aisles = SelectField("Aisle", choices=['No Aisles Yet'], default=['No Aisles Yet'], id=[])
    unadded = SelectMultipleField("Ingredients", choices=['No Ingredients Yet'], default=['No Ingredients Yet'])
    submit = SubmitField('Add')
