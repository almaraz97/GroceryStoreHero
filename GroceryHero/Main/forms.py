from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, SelectMultipleField, StringField


class ImportForm(FlaskForm):
    file_name = FileField('Upload recipe file', validators=[FileAllowed(['txt'], 'Text Files Only'), FileRequired()])
    import_recipes_button = SubmitField('Recipes')
    import_aisles_button = SubmitField('Aisles')


class ExportForm(FlaskForm):
    export_recipes_button = SubmitField('Export Recipes')
    export_aisles_button = SubmitField('Export Aisles')


class ExtrasForm(FlaskForm):
    content = SelectMultipleField('Ingredients', choices=[], default=['<--Choose-->'])
    other = StringField(label='Other (separate with commas)')
    submit = SubmitField('Next')

# class AddExtrasForm(FlaskForm):
#     aisle_forms = FieldList(FormField(ExtrasForm), min_entries=1)
#     submit = SubmitField('Add')
