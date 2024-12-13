# app.py
from flask import Flask
from flask_restful import Api
from Resources.auth import Register, Login


app = Flask(__name__)
api = Api(app)

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')

if __name__ == "__main__":
    app.run(debug=True)

