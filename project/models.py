from datetime import datetime

from flask_login import UserMixin
from sqlalchemy.orm import relationship

from . import db


class User(UserMixin, db.Model):
    """Данные о пользователе"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    items = db.relationship('Item', backref='user')


class Item(db.Model):
    """Данные об обьявлениях"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    description = db.Column(db.String(500))
    price = db.Column(db.Integer, nullable=False)
    final_date = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    buyer = db.Column(db.String(100), nullable=True, default="Пока никому. Станьте первым!")

    def __repr__(self):
        # final_date = str(self.final_date)[:-3]
        # final_date_from_timestamp = datetime.utcfromtimestamp(int(final_date))   из кодировки UNIX
        return f'{self.id}'
