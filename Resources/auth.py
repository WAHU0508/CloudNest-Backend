# Resources/auth.py
from flask_restful import Resource
from flask import request, jsonify
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from supabase_client import supabase
import re

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

TOKEN_BLACKLIST = set()

# <local-part>@<domain>.<TLD>
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class Register(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        # Validate missing fields
        if not username or not email or not password or not confirm_password:
            return {"error": "Missing required fields."}, 400

        # Check if passwords match
        if password != confirm_password:
            return {"error": "Passwords do not match"}, 400
        
        #Validate email
        if not re.match(EMAIL_REGEX, email):
            return {"error": "Invalid email format"}, 400

        # Check if user exists
        existing_username = supabase.table("users").select("*").eq("username", username).execute()
        existing_email = supabase.table("users").select("*").eq("email", email).execute()
        if existing_username.data:
            return {"error": "Username already exists"}, 409
        if existing_email.data:
            return {"error": "Email already exists"}, 409

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Insert new user into Supabase
        new_user = supabase.table("users").insert({
            "username": username,
            "email": email,
            "password": hashed_password
        }).execute()

        return {"message": "User registered successfully"}, 201

class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        #validation
        if not email or not password:
            return {"error": "Missing required fields"}, 400

        #Get user from db
        user = supabase.table("users").select("*").eq("email", email).execute()
        if not user.data:
            return {"error": "User doesn't exist"}, 404
        user = user.data[0]

        #Check password
        if not check_password_hash(user["password"], password):
            return {"error": "Invalid password"}, 401
        
        #Generate token
        payload = {
            "user_id": user["id"],
            "exp": datetime.utcnow() + timedelta(hours=1) #Token expires in 1 hour
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return {"token": token, "id": user["id"], "username": user["username"], "email": user["email"]}, 200


class Logout(Resource):
    def post(self):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return {"error": "Authorization token is missing"}, 400
        
        # Extract the token
        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return {"error": "Invalid token format"}, 400
        
        # Decode the token to validate it (optional)
        try:
            jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return {"error": "Token has already expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401

        # Add the token to the blacklist
        TOKEN_BLACKLIST.add(token)

        return {"message": "Logged out successfully"}, 200
