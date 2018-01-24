from flask_wtf import Form
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, DataRequired, Email, EqualTo
from wtforms import ValidationError
from app.models import User


class LoginForm(Form):
    """Login form used for HTML login
    """

    email = StringField(
        'Email', validators=[DataRequired(),
                             Length(1, 64),
                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class PasswordResetForm(Form):
    email = StringField(
        'Email', validators=[DataRequired(),
                             Length(1, 64),
                             Email()])
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            EqualTo('confirm_password', message='Passwords must match')
        ])
    confirm_password = PasswordField(
        'Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('Unknown email address.')


class SetPasswordForm(Form):
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(12),
            EqualTo('confirm_password', message='Passwords must match')
        ])
    confirm_password = PasswordField(
        'Confirm password', validators=[DataRequired()])
    submit = SubmitField('Set Password')
