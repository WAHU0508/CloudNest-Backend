from flask import Flask, request, jsonify, abort
import os
import hashlib
import time
from flask_restful import Resource, Api
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
from datetime import datetime
from supabase_client import supabase

app = Flask(__name__)
api = Api(app)

# Folders functions
STORAGE_DIR = os.path.join(os.getcwd(), 'uploads')

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)


def get_folders(user_id):
    """Returns a list of all folder names."""

    user_folder_path = os.path.join(STORAGE_DIR, int(user_id))
    if not os.path.exists(user_folder_path):
        return []  

    return [folder for folder in os.listdir(user_folder_path) if os.path.isdir(os.path.join(user_folder_path, folder))]

def create_folder(folder_name, user_id):
    """Create a new folder for the user and add it to the Supabase database."""
    user_folder_path = os.path.join(STORAGE_DIR, int(user_id), folder_name)
    
    if os.path.exists(user_folder_path):
        return {"success": False, "message": "Folder already exists"}

    try:
        user_specific_dir = os.path.join(STORAGE_DIR, int(user_id))
        if not os.path.exists(user_specific_dir):
            os.makedirs(user_specific_dir) 

        os.makedirs(user_folder_path)

        folder_data = {
            "folder_name": folder_name,
            "user_id": user_id,
            "created_at": datetime.now()
        }

        response = supabase.table('folders').insert(folder_data).execute()

        print(f"Created folder details: {folder_data}")

        if response.status_code == 201:
            return {"success": True, "message": "Folder created successfully and added to the database"}
        else:
            return {"success": False, "message": "Failed to add folder to database"}
        
    except OSError as e:
        return {"success": False, "message": f"Failed to create folder: {str(e)}"}
    

def update_folder(old_name, new_name, user_id):
    old_path = os.path.join(STORAGE_DIR, int(user_id), old_name)
    new_path = os.path.join(STORAGE_DIR, int(user_id), new_name)

    if not os.path.exists(old_path):
        return {"success": False, "message": "Folder not found"}
    if os.path.exists(new_path):
        return {"success": False, "message": "New folder name already exists"}

    try:
        os.rename(old_path, new_path)
        response = supabase.table('folders').update({"folder_name": new_name}).eq('folder_name', old_name).eq('user_id', user_id).execute()

        if response.status_code == 200:
            return {"success": True, "message": "Folder name updated successfully"}
        else:
            return {"Success": False, "message": "Failed to update folder name in database"}
    except OSError as e:
        return {"success": False, "message": f"Error renaming folder: {str(e)}"}

def delete_folder(folder_name, user_id):
    """Deletes a folder and its contents."""
    folder_path = os.path.join(STORAGE_DIR, int(user_id), folder_name)

    if not os.path.exists(folder_path):
        return {"success": False, "message": "Folder not found"}

    try:
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)

        response = supabase.table('folders').delete().eq('folder_name', folder_name).eq('user_id', user_id).execute()

        if response.status_code == 200:
            return {"success": True, "message": "Folder deleted successfully"}
        else:
            return{"success": False, "message": "Failed to delete folder from database"}
    except OSError as e:
        return {"success": False, "message": f"Error deleting folder: {str(e)}"}


class Folder(Resource):
    def get(self, folder_id=None):
        """Get all folders or a specific folder by folder_id."""

        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized, please log in"}), 401

        if folder_id is None:
            folders = get_folders(current_user.id)
            return jsonify({'folders': folders}), 200

        folder_path = os.path.join(STORAGE_DIR, int(current_user.id), folder_id)
        if os.path.exists(folder_path):
            return jsonify({'folder': folder_id}), 200
        else:
            return jsonify({'error': 'Folder not found'}), 404

    def patch(self, folder_id):
        """Update folder name."""
        new_name = request.json.get('new_name')
        if not new_name:
            return jsonify({'error': 'New folder name is required'}), 400

        result = update_folder(folder_id, new_name, current_user.id)
        if result['success']:
            return jsonify({'message': result['message'], 'new_name': new_name}), 200
        else:
            return jsonify({'error': result['message']}), 400

    def delete(self, folder_id):
        """Delete a folder."""
        result = delete_folder(folder_id, current_user.id)
        if result['success']:
            return jsonify({'message': result['message']}), 200
        else:
            return jsonify({'error': result['message']}), 404

api.add_resource(Folder, '/folders', '/folders/<string:folder_id>')