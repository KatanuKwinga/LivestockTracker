"""Flask-WTF forms for authentication."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from app.models import User


class FarmerRegistrationForm(FlaskForm):
    """A brand-new farmer creating their own account. This is the only
    self-registration path in the whole app"""

    name = StringField("Full name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField("Phone (optional)", validators=[Optional(), Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        # Runs automatically because WTForms looks for a method named validate_<fieldname>. We check for an existing account here. 
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class WorkerCreationForm(FlaskForm):
    """Used by a logged-in farmer to create an account for one of their
    workers. The farmer sets the worker's initial password directly.
    there's no email-verification at this stage."""

    name = StringField("Worker's full name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Worker's email", validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField("Phone (optional)", validators=[Optional(), Length(max=20)])
    password = PasswordField("Temporary password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create worker account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")
