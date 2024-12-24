# app.py
from flask import Flask, request, jsonify
from flask_restful import Api
from Resources.auth import Register, Login
from Resources.files import UploadFile
from Resources.files_folders import Folder, create_folder
from flask_login import current_user, login_required


app = Flask(__name__)
api = Api(app)

app.route('/')
def index():
    return "<h1>Welcome to CloudNest</h1>"

@app.route('/create-folder', methods=["POST"])
def create_folder_route():
    """Create a folder for the logged-in user."""
    folder_name = request.json.get('folder_name')
    
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400

    result = create_folder(folder_name, current_user.id)
    
    if result['success']:
        return jsonify({'message': result['message'], 'folder_name': folder_name}), 201
    else:
        return jsonify({'error': result['message']}), 400
    

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Folder, '/folders')
api.add_resource(Logout, '/logout')
api.add_resource(UploadFile, '/upload_file')


if __name__ == "__main__":
    app.run(debug=True)

