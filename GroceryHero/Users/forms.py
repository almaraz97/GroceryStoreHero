from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, SelectField, SelectMultipleField, \
    FormField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from flask_login import current_user
from GroceryHero.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign up')

    # def validate_username(self, username):
    #     user = User.query.filter_by(username=username.data).first()
    #     if user:
    #         raise ValidationError('That username is taken. Please choose a different one.')

    @staticmethod
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        pass
    #     if username.data != current_user.username:
    #         user = User.query.filter_by(username=username.data).first()
    #         if user:
    #             raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    @staticmethod
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Please choose a different one.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Submit')


class DeleteAccountForm(FlaskForm):
    submit = SubmitField('Delete')


class HarmonyForm(FlaskForm):
    groups = SelectField("Number of Recipes per Recommendation", choices=[(x, x) for x in range(1, 5)], coerce=int)
    excludes = SelectMultipleField("Exclude Recipes", choices=[])
    similarity = SelectField("Maximum Harmony", choices=[(x, x) for x in range(10, 90, 10)] +
                                                        [(float('inf'), 'No limit')], coerce=float)
    submit = SubmitField('Harmonize')


class AdvancedHarmonyForm(FlaskForm):
    pairs = SelectMultipleField("Recipes", choices=[])
    pair_weight = SelectField("Weight", choices=[(x, x) for x in range(1, 6)], default=1)

    ingredient = SelectMultipleField("Ingredient", choices=[])
    ingredient_weights = SelectField("Weight", choices=[(x, x) for x in
                                                        [0.001, 0.4, 0.6, 0.8, 1.0, 2.0, 3.0, 4.0, 10.0]], default=1.0)
    delete_weights = SubmitField('Delete All Weights')

    ingredient_ex = SelectMultipleField('Ingredients', choices=[])
    ingredient_rem = SelectMultipleField('Ingredients', choices=[])

    ingredient2 = SelectMultipleField("Ingredient", choices=[])
    sticky_weights = SelectField("Weight", choices=[(x,x) for x in range(6)], default=0)

    history_exclude = SelectField("Menu Weight", choices=[(x,x) for x in range(6)], default=0)

    recommend_num = SelectField("Max Number of Recommendations", choices=[(x,x) for x in range(3,11)], default=3)
    algorithm = SelectField("Algorithm", choices=['Charity', 'Fairness', 'Balanced', 'Selfish', 'Greedy'],
                            default='Balanced')
    modifier = SelectField("Scoring", choices=['True', 'Graded'],
                           default='Graded')
    submit = SubmitField('Submit')


class FullHarmonyForm(FlaskForm):
    basic = FormField(HarmonyForm)
    advanced = FormField(AdvancedHarmonyForm)
    submit = SubmitField('Submit')


class FriendForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "Followees Email Address"})
    submit = SubmitField('Request')


class FollowForm(FlaskForm):
    add = SubmitField('Add')
    ignore = SubmitField('Ignore')
    block = SubmitField('Block')

