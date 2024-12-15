from flask import Flask, request, jsonify
import os
import hashlib
import time
from flask_restful import Resource, Api
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_required
from datetime import datetime
from supabase_client import supabase

app = Flask(__name__)
api = Api(app)
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'upload/'
ALLOWED_EXTENSIONS = {'txt', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'svg', 'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

STORAGE_DIR = os.path.join(os.getcwd(), 'uploads')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(filename):
    hash_object = hashlib.sha256(filename.encode())
    timestamp = str(int(time.time()))  # Optional: Append timestamp to ensure uniqueness
    return f"{timestamp}_{hash_object.hexdigest()}_{filename}"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')

    if not files:
        return jsonify({"error": "No file selected"}), 400
    
    filenames = []

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    for file in files:
        if file and allowed_file(file.filename):
            filename = get_unique_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)

            try:
                response = supabase.table('files').insert({
                    "file_name": filename,
                    "user_id": current_user.id,
                    "file_size": file_size,
                    "storage_path": file_path,
                    "folder_id": None
                }).execute()

                if response.status_code == 201:
                    filenames.append(filename)
                else:
                    raise Exception(f"Error inserting file record: {response.error_message}")

            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({"error": f"An error occurred while saving the file: {str(e)}"}), 500
        else:
            return jsonify({"error": "Invalid file type or missing file"}), 400

    return jsonify({"message": "Files uploaded successfully", "filenames": filenames}), 200


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "File is too large, please upload files smaller than 25MB."}), 413


if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def get_folders():
    """Returns a list of all folder names."""
    if not os.path.exists(STORAGE_DIR):
        return []  

    return [folder for folder in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, folder))]

def create_folder(folder_name, user_id):
    """Create a new folder for the user and add it to the Supabase database."""
    
    user_folder_path = os.path.join(STORAGE_DIR, str(user_id), folder_name)
    
    if os.path.exists(user_folder_path):
        return {"success": False, "message": "Folder already exists"}

    try:
        user_specific_dir = os.path.join(STORAGE_DIR, str(user_id))
        if not os.path.exists(user_specific_dir):
            os.makedirs(user_specific_dir) 

        os.makedirs(user_folder_path)

        folder_data = {
            "folder_name": folder_name,
            "user_id": user_id,
            "created_at": datetime.now()
        }

        response = supabase.table('folders').insert(folder_data).execute()

        if response.status_code == 201:
            return {"success": True, "message": "Folder created successfully and added to the database"}
        else:
            return {"success": False, "message": "Failed to add folder to database"}
        
    except OSError as e:
        return {"success": False, "message": f"Failed to create folder: {str(e)}"}
    

def update_folder(old_name, new_name):
    old_path = os.path.join(STORAGE_DIR, old_name)
    new_path = os.path.join(STORAGE_DIR, new_name)

    if not os.path.exists(old_path):
        return {"success": False, "message": "Folder not found"}
    if os.path.exists(new_path):
        return {"success": False, "message": "New folder name already exists"}

    try:
        os.rename(old_path, new_path)
        return {"success": True, "message": "Folder name updated successfully"}
    except OSError as e:
        return {"success": False, "message": f"Error renaming folder: {str(e)}"}

def delete_folder(folder_name):
    """Deletes a folder and its contents."""
    folder_path = os.path.join(STORAGE_DIR, folder_name)

    if not os.path.exists(folder_path):
        return {"success": False, "message": "Folder not found"}

    try:
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)
        return {"success": True, "message": "Folder deleted successfully"}
    except OSError as e:
        return {"success": False, "message": f"Error deleting folder: {str(e)}"}


class Folder(Resource):
    def get(self, folder_id=None):
        """Get all folders or a specific folder by folder_id."""
        if folder_id is None:
            folders = get_folders()
            return jsonify({'folders': folders})

        folder_path = os.path.join(STORAGE_DIR, folder_id)
        if os.path.exists(folder_path):
            return jsonify({'folder': folder_id}), 200
        else:
            return jsonify({'error': 'Folder not found'}), 404

    def patch(self, folder_id):
        """Update folder name."""
        new_name = request.json.get('new_name')
        if not new_name:
            return jsonify({'error': 'New folder name is required'}), 400

        result = update_folder(folder_id, new_name)
        if result['success']:
            return jsonify({'message': result['message'], 'new_name': new_name}), 200
        else:
            return jsonify({'error': result['message']}), 400

    def delete(self, folder_id):
        """Delete a folder."""
        result = delete_folder(folder_id)
        if result['success']:
            return jsonify({'message': result['message']}), 200
        else:
            return jsonify({'error': result['message']}), 404

api.add_resource(Folder, '/folders', '/folders/<string:folder_id>')

def add_file_to_folder(file_id, folder_id):
    """Move a file into a folder."""
    file = supabase.table('files').select("*").eq("id", file_id).execute()

    if not file or len(file['data']) == 0:
        return jsonify({'error': 'File not found'}), 404

    file = file['data'][0]
    old_path = file['storage_path']
    new_path = os.path.join(STORAGE_DIR, folder_id, file['file_name'])

    if not os.path.exists(os.path.join(STORAGE_DIR, folder_id)):
        os.makedirs(os.path.join(STORAGE_DIR, folder_id))

    try:
        os.rename(old_path, new_path)
        
        response = supabase.table('files').update({"folder_id": folder_id, "storage_path": new_path}).eq("id", file_id).execute()

        return jsonify({"message": "File moved to folder", "file_name": file['file_name']}), 200

    except OSError as e:
        return jsonify({'error': f"Error moving file: {str(e)}"}), 500
    
def remove_file_from_folder(file_id):
    """Remove a file from a folder by setting folder_id to None in the database."""
    
    file = supabase.table('files').select("*").eq("id", file_id).execute()

    if not file or len(file['data']) == 0:
        return jsonify({'error': 'File not found'}), 404

    file = file['data'][0]
    old_folder_id = file['folder_id']
    file_name = file['file_name']
    old_storage_path = file['storage_path']

    if old_folder_id is None:
        return jsonify({'message': 'File is already not associated with any folder'}), 400

    try:
        response = supabase.table('files').update({
            "folder_id": None, 
        }).eq("id", file_id).execute()

        if response.status_code == 200:
            new_storage_path = os.path.join(STORAGE_DIR, file_name)
            
            if old_storage_path != new_storage_path:
                os.rename(old_storage_path, new_storage_path)

            return jsonify({"message": "File removed from folder", "file_name": file_name}), 200
        else:
            return jsonify({'error': 'Failed to update the file in the database'}), 500

    except Exception as e:
        return jsonify({'error': f"Error removing file from folder: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)