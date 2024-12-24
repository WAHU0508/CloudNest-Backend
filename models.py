# models.py
from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_login import UserMixin
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Flask-Migrate for database migrations
migrate = Migrate(app)

# Define the User model using SQLAlchemy
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.username}, {self.email}>"
        
