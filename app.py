# app.py
from flask import Flask
from flask_restful import Api
from Resources.auth import Register, Login
from Resources.files_folders import Folder


app = Flask(__name__)
api = Api(app)

app.route('/')
def index():
    return "<h1>Welcome to CloudNest</h1>"

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Folder, '/folders')


if __name__ == "__main__":
    app.run(debug=True)

