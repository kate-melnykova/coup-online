from typing import List

from wtforms import Form
from wtforms import StringField, SelectMultipleField
from wtforms import Field, PasswordField, BooleanField, DateField, TextAreaField
from wtforms.validators import ValidationError
from wtforms.fields.html5 import EmailField
from wtforms import validators


strip_filter = lambda x: x.strip() if x else None


def no_special_symbols(form, field):
    if not all(char.isalnum() for char in field.data):
        raise ValidationError('Field has characters that are not allowed!')


class CreateOrJoinGameForm(Form):
    name = StringField('Enter your name*:', [validators.DataRequired(),
                                validators.Length(min=1, max=15),
                                no_special_symbols,
                                ])
    n_players = StringField('Enter the number of players (including you)')
    game_id = StringField('Game id (provided by the dealer)')

