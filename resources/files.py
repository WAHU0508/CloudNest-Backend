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


UPLOAD_FOLDER = 'upload/'
ALLOWED_EXTENSIONS = {'txt', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'svg', 'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024


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
