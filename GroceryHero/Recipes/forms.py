from flask_wtf import FlaskForm
from werkzeug.routing import ValidationError
from wtforms import StringField, SubmitField, TextAreaField, SelectField, FloatField, FieldList, FormField
from wtforms.validators import InputRequired, DataRequired, number_range


class Measurements:
    Measures = ['Unit', 'Package', 'Can', 'Bottle', 'Jar', 'US Cup', 'US Tablespoon', 'US Teaspoon', 'US Fluid Ounce',
                'Ounce', 'Pound', 'Milligram', 'Gram', 'Kilogram', 'Milliliter', 'Liter']
    # 'US Pint', 'US Quart', 'US Gallon',

    Volumes = ['US Cup', 'US Fluid Ounce', 'US Tablespoon', 'US Teaspoon']  # 'US Gallon', 'US Quart', 'US Pint',
    Weights = ['Pound', 'Ounce']
    Generic = ['Unit', 'Package', 'Can', 'Bottle', 'Jar']

    Metric_Volumes = ['Liter', 'Milliliter']
    Metric_Weights = ['Kilogram', 'Gram', 'Milligram']

    Convert = {'US Gallon': 768, 'US Quart': 192, 'US Pint': 96, 'US Cup': 48.6922, 'US Fluid Ounce': 6,
               'US Tablespoon': 3, 'US Teaspoon': 1, 'Liter': 1000, 'Milliliter': 1, 'Pound': 16, 'Ounce': 1,
               'Kilogram': 1e+6, 'Gram': 1000, 'Milligram': 1}  # To lowest [teaspoon, ounce, milligram]

    # Dict_func = (lambda V=Volumes, W=Weights, G=Generic, MV=Metric_Volumes, M=Measures:
    #              {x: ('Volume' if x in V else
    #                   ('Weight' if x in W else
    #                    ('Generic' if x in G else
    #                     ('Metric_Volumes' if x in MV else 'Metric_Weights')))) for x in M})
    # Measure_dict = Dict_func()

    def __init__(self, value, unit):
        if unit not in self.Measures:
            raise AssertionError("Must be in Measurements")
        self.metric = True if unit in ['Milligram', 'Gram', 'Kilogram', 'Liter', 'Milliliter'] else False
        self.value = value
        self.unit = unit
        if self.unit in self.Generic:
            self.type = 'Generic'
        else:
            if self.metric:  # Should I do both volumes/weight or Volume_metric/Weight_metric
                self.type = 'Volume' if self.unit in self.Metric_Volumes else 'Weight'
            else:
                self.type = 'Volume' if self.unit in self.Volumes else 'Weight'

    def __add__(self, other, rounding=2):
        if not isinstance(other, Measurements):
            raise AssertionError('Must be of class Measurements')
        if not self.metric == other.metric:
            raise AssertionError('Must agree in measurement system')
        if self.type != other.type:
            AssertionError('Cannot add objects of different measure types')
        if self.type == 'Generic':
            if self.unit == other.unit:
                total = self.value + other.value
                return Measurements(round(total, rounding), unit=self.unit)
            else:
                raise AssertionError('Must agree in Generic unit')

        self.value = self.Convert[self.unit] * self.value  # convert to lowest
        other.value = other.Convert[other.unit] * other.value  # convert to lowest
        total = self.value + other.value
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    return Measurements(round(total, 2), unit=volume)
        else:
            weights = self.Metric_Weights if self.metric else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    return Measurements(round(total, 2), unit=weight)

    def __sub__(self, other, rounding=2):
        if not isinstance(other, Measurements):
            raise AssertionError('Must be of class Measurements')
        if not self.metric == other.metric:
            raise AssertionError('Must agree in measurement system')
        if self.type != other.type:
            AssertionError('Cannot add objects of different measure types')
        if self.type == 'Generic':
            if self.unit == other.unit:
                total = self.value - other.value
                return Measurements(round(total, rounding), unit=self.unit)
            else:
                raise AssertionError('Must agree in Generic unit')

        self.value = self.Convert[self.unit] * self.value  # convert to lowest
        other.value = other.Convert[other.unit] * other.value  # convert to lowest
        total = self.value - other.value
        if self.type == 'Volume':
            volumes = self.Metric_Volumes if self.metric else self.Volumes
            for volume in volumes:  # Go up through conversion until whole number
                if int(total / self.Convert[volume]) >= 1:
                    total = total / self.Convert[volume]
                    return Measurements(round(total, 2), unit=volume)
        else:
            weights = self.Metric_Weights if self.metric else self.Weights
            for weight in weights:
                if int(total / self.Convert[weight]) >= 1:
                    total = total / self.Convert[weight]
                    return Measurements(round(total, 2), unit=weight)

    def __eq__(self, other):  # todo should I include value as part of equivalence?
        if not isinstance(other, Measurements):
            raise AssertionError('Must be of class Measurements')
        return self.type == other.type and self.metric == other.metric

    def __repr__(self):
        if self.value != 1:
            return f'{self.value} {self.unit}s'
        else:
            return f'{self.value} {self.unit}'


# class MyFloatField(FloatField):
#     def process_data(self, valuelist):
#         if valuelist:
#             if valuelist.count('/') == 1:
#                 try:
#                     numbers = valuelist.split('/')
#                     self.data = numbers[0]/numbers[1]
#                 except ValueError:
#                     self.data = None
#                     raise ValueError(self.gettext('Not a valid division'))
#             else:
#                 try:
#                     self.data = valuelist[0]
#                 except ValueError:
#                     self.data = None
#                     raise ValueError(self.gettext('Not a valid float value'))


class RecipeForm(FlaskForm):
    title = StringField('Recipe Name', validators=[DataRequired()])
    content = TextAreaField('Ingredients (separate with commas)', validators=[DataRequired()])
    notes = TextAreaField('Notes (optional)')
    submit = SubmitField('Next')


class QuantityForm(FlaskForm):
    ingredient_quantity = StringField('Quantity', default=1.0, validators=[InputRequired()])
    ingredient_type = SelectField("Measurement", choices=[(x, x) for x in Measurements.Measures], default='Unit')

    @staticmethod
    def validate_ingredient_quantity(self, field):
        try:  # is just a float
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
