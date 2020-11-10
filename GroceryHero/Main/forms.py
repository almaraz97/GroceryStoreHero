from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, SelectMultipleField, StringField
from wtforms.validators import DataRequired


class ImportForm(FlaskForm):
    file_name = FileField('Upload recipe file', validators=[FileAllowed(['txt'], 'Text Files Only'), FileRequired()])
    import_recipes_button = SubmitField('Recipes')
    import_aisles_button = SubmitField('Aisles')


class ExportForm(FlaskForm):
    export_recipes_button = SubmitField('Export Recipes')
    export_aisles_button = SubmitField('Export Aisles')


class ExtrasForm(FlaskForm):
    multi = SelectMultipleField('Ingredients', choices=[], default=['<--Choose-->'])
    other = StringField(label='Other (separate with commas)')
    submit = SubmitField('Next')

    def validate(self, extra_validators=None):
        if super().validate(extra_validators):
            # Check at least one form is filled
            if not (self.multi.data or self.other.data):
                self.multi.errors.append('At least one field must have a value')
                return False
            else:
                return True
        return False

