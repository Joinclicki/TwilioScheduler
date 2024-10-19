from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates, relationship
import re
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    scheduled_blasts = relationship('ScheduledBlast', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Recipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    custom_fields = db.Column(db.JSON)
    blast_associations = relationship('RecipientBlastAssociation', back_populates='recipient')

    @validates('phone_number')
    def validate_phone_number(self, key, phone_number):
        if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
            raise ValueError('Invalid phone number format. Must be in E.164 format.')
        return phone_number

class ScheduledBlast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship('User', back_populates='scheduled_blasts')
    blast_name = db.Column(db.String(100), nullable=False)  # New field
    message_template = db.Column(db.Text, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    twilio_message_sid = db.Column(db.Text)
    recipient_associations = relationship('RecipientBlastAssociation', back_populates='scheduled_blast', cascade='all, delete-orphan')

    def set_twilio_message_sids(self, sids):
        self.twilio_message_sid = json.dumps(sids)

    def get_twilio_message_sids(self):
        return json.loads(self.twilio_message_sid) if self.twilio_message_sid else []

class RecipientBlastAssociation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('recipient.id'), nullable=False)
    scheduled_blast_id = db.Column(db.Integer, db.ForeignKey('scheduled_blast.id'), nullable=False)
    recipient = relationship('Recipient', back_populates='blast_associations')
    scheduled_blast = relationship('ScheduledBlast', back_populates='recipient_associations')
