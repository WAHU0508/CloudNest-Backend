from flask_restful import Resource
from flask import request, jsonify
import jwt
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for file uploads

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def authenticate_token(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = decoded.get("user_id")
        if not user_id:
            raise ValueError("Token is missing 'user_id'")
        return user_id
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def check_user_permission(user_id):
    # Check if user_id exists in the 'users' table or any other relevant table
    result = supabase.table('users').select('id').eq('id', user_id).execute()
    if result.data:
        return True
    return False

class UploadFile(Resource):
    def post(self):
        # Check if the user is authenticated
        token = request.headers.get("Authorization")
        if not token:
            return {"error": "Unauthorized, please provide a token"}, 401

        try:
            # Authenticate and get the user_id from the token
            user_id = authenticate_token(token)
            print(f"Authenticated user ID: {user_id}")  # Debug log for user ID

            # Check if the user has permission to upload
            if not check_user_permission(user_id):
                return {"error": "User does not have permission to upload files"}, 403

            # Check if the file part is in the request
            if 'file' not in request.files:
                return {"error": "No file part in the request"}, 400
            
            file = request.files['file']
            if file.filename == '':
                return {"error": "No selected file"}, 400
            
            # File size validation
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer after checking size
            if file_size > MAX_FILE_SIZE:
                return {"error": f"File size exceeds the {MAX_FILE_SIZE // 1024 // 1024}MB limit"}, 400

            print(f"File size: {file_size} bytes")  # Debug log for file size

            # Save the file locally before uploading to Supabase
            filename = secure_filename(file.filename)
            local_file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(local_file_path)

            # Generate a unique file path for Supabase
            storage_bucket = supabase.storage.from_('uploaded_files')
            file_path_supabase = f"files/{str(uuid.uuid4())}/{filename}"

            # Upload to Supabase
            with open(local_file_path, 'rb') as f:
                upload_response = storage_bucket.upload(file_path_supabase, f)
                print(f"Upload Response: {upload_response}")  # Debugging the response

                # Check if the upload was successful
                if hasattr(upload_response, 'status_code') and upload_response.status_code != 200:
                    return {"error": "Failed to upload file to Supabase"}, 500

                if not hasattr(upload_response, 'path'):
                    return {"error": "Failed to upload file to Supabase"}, 500

            # Get the public URL of the uploaded file
            file_url = storage_bucket.get_public_url(file_path_supabase)
            if not file_url:
                return {"error": "Failed to retrieve file URL from Supabase"}, 500

            # Convert datetime objects to ISO 8601 string format
            current_time = datetime.utcnow().isoformat()

            # Store metadata in the Supabase 'files' table
            file_metadata = {
                "file_name": filename,
                "file_size": file_size,
                "storage_path": file_url,
                "user_id": user_id,
                "folder_id": None,
                "uploaded_at": current_time,
                "updated_at": current_time, 
                "deleted_at": None
            }

            # Insert metadata
            response = supabase.table("files").insert(file_metadata).execute()
            print(f"Insert Response: {response}")  # Debugging to check the response structure

            # Ensure that the response contains 'data' indicating successful insertion
            if not response or not hasattr(response, 'data') or not response.data:
                return {"error": "Failed to save metadata to Supabase"}, 500

            # Clean up the local file
            os.remove(local_file_path)

            return {"message": "File uploaded successfully", "file_url": file_url}, 200

        except ValueError as e:
            return {"error": str(e)}, 401
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}, 500