import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_migrate import Migrate

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY") or "a_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    import models
    import auth
    from message_scheduler import message_scheduler
    # Remove the following line as it's already registered in message_scheduler.py
    # app.register_blueprint(message_scheduler)

@app.route('/')
def index():
    return redirect(url_for('message_scheduler.dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
