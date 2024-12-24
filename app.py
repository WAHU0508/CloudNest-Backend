# app.py
from flask import Flask, request, jsonify
from flask_restful import Api
from resources.auth import Register, Login
from resources.folders import Folder, create_folder
from flask_login import current_user, login_required, login_user, UserMixin, LoginManager
from flask_cors import CORS
from supabase_client import supabase
from models import User


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)
CORS(app)

app.route('/')
def index():
    return "<h1>Welcome to CloudNest</h1>"

@login_manager.user_loader
def load_user(user_id):
    user = supabase.table("users").select("*").eq("id", user_id).execute()

    if user.data:
        user_data = user.data[0]
        return User(user_data["id"], user_data["username"], user_data["email"])
    
    return None

@app.route('/api/create-folder', methods=["POST"])
@login_required
def create_folder_route():
    """Create a folder for the logged-in user."""
    print(f"Current user: {current_user}")
    folder_name = request.json.get('folder_name')
    
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400
    
    user_id = current_user.id

    if not user_id:
        return jsonify({"message": "No user logged in"}), 400

    result = create_folder(folder_name, user_id)
    
    if result['success']:
        return jsonify({'message': result['message'], 'folder_name': folder_name}), 201
    else:
        return jsonify({'error': result['message']}), 400
    

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Folder, '/api/folders')


if __name__ == "__main__":
    app.run(port=5555, debug=True)

