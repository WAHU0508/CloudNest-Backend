# app.py
from flask import Flask
from flask_restful import Api
from Resources.auth import Register, Login, Logout
from Resources.files import UploadFile


app = Flask(__name__)
api = Api(app)

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(UploadFile, '/upload_file')

if __name__ == "__main__":
    app.run(debug=True)

