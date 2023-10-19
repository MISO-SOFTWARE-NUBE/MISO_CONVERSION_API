from . import create_app
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from flask_jwt_extended import JWTManager
from datetime import timedelta
from .src.models import db
from .src.views import VistaSolicitud, VistaLogIn, VistaSignUp, VistaSolicitudes

app = create_app('default')
app_context = app.app_context()
app_context.push()

db.init_app(app)
db.create_all()

cors = CORS(app)

api = Api(app)
api.add_resource(VistaSolicitud, '/api/task/<string:download_type>/<int:file_id>',
                 '/api/task/', '/api/delete-task/<int:file_id>/')
api.add_resource(VistaSolicitudes, '/api/all_task/')
api.add_resource(VistaLogIn, '/api/auth/login/')
api.add_resource(VistaSignUp, '/api/auth/signup/')

jwt = JWTManager(app)
