# auth/auth.py
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
            return jsonify({"error": "Missing required fields."}), 400

        # Check if passwords match
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400
        
        #Validate email
        if not re.match(EMAIL_REGEX, email):
            return jsonify({"error": "Invalid email format"}), 400

        # Check if user exists
        existing_username = supabase.table("users").select("*").eq("username", username).execute()
        existing_email = supabase.table("users").select("*").eq("email", email).execute()
        if existing_username.data:
            return jsonify({"error": "Username already exists"}), 409
        if existing_email.data:
            return jsonify({"error": "Email already exists"}), 409

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Insert new user into Supabase
        new_user = supabase.table("users").insert({
            "username": username,
            "email": email,
            "password": hashed_password
        }).execute()

        return jsonify({"message": "User registered successfully"}), 201

class Login(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        #validation
        if not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        #Get user from db
        user = supabase.table("users").select("*").eq("email", email).execute()
        if not user.data:
            return jsonify({"error": "User doesn't exist"}), 404
        user = user.data[0]

        #Check password
        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid password"}), 401
        
        #Generate token
        payload = {
            "user_id": user["id"],
            "exp": datetime.utcnow() + timedelta(hours=1) #Token expires in 1 hour
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return {"token": token, "id": user["id"], "username": user["username"], "email": user["email"]}, 200
