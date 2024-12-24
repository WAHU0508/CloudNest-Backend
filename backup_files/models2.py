# models.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_login import UserMixin
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure PostgreSQL URI from the .env file
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Migrate for database migrations
migrate = Migrate(app, db)

# Define the User model using SQLAlchemy
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.username}, {self.email}>"
        

class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.String, nullable=False)
    file_size = db.Column(db.Text)
    storage_path = db.Column(db.Text)
    folder_id = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, onupdate= func.now())
    deleted_at = db.Column(db.DateTime, default=func.now())


class Folder(db.Model):
    __tablename__ = 'folders'

    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, onupdate= func.now())
    deleted_at = db.Column(db.DateTime, default=func.now())
