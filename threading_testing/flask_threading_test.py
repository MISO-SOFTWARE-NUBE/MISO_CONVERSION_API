
from sqlalchemy.orm import scoped_session
from flask import current_app
import os
from datetime import datetime
import subprocess
import tempfile
import base64
import threading

from flask import request, current_app
from flask_cors import CORS
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource
from google.cloud import storage

from src_worker import create_app
# from utils import get_blob_name_fr

db = SQLAlchemy()


class Solicitudes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    input_path = db.Column(db.String(500))
    output_path = db.Column(db.String(500))
    input_format = db.Column(db.String(5))
    output_format = db.Column(db.String(5))
    fileName = db.Column(db.String(500))
    upload_date = db.Column(db.DateTime)
    start_process_date = db.Column(db.DateTime)
    end_process_date = db.Column(db.DateTime)
    status = db.Column(db.String(50))


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(128))
    email = db.Column(db.String(128))
    password = db.Column(db.String(128))


app = create_app('default')
app_context = app.app_context()
app_context.push()

db.init_app(app)
db.create_all()

cors = CORS(app)

api = Api(app)

# client = storage.Client()
# bucket = client.bucket(current_app.config['UPLOAD_BUCKET'])


def process_task(app, id):
    with app.app_context():
        # Create a scoped session for thread safety
        # session = scoped_session(db.session)
        session = scoped_session(db.sessionmaker(bind=db.engine))

        try:
            # 1. Query record in database with new session
            record = session.query(Solicitudes).get(int(id))

            # Check if record is found
            if not record:
                print(f"Record with id {id} not found.")
                return

            # 2. Register start_processing_time and update status
            record.start_process_date = datetime.now()
            record.status = "in_process"
            session.commit()

            # Get paths to files
            full_input_path = os.path.join(
                record.input_path, f"{record.fileName}.{record.input_format}")
            full_output_path = os.path.join(
                record.output_path, f"{record.fileName}.{record.output_format}")

            # If output folder does not exist, make it
            if not os.path.exists(record.output_path):
                os.makedirs(record.output_path)

            # Convert and save file
            cmd = ['ffmpeg', '-i', full_input_path, full_output_path]
            print("🌪️🌪️🌪️ Started converting")
            result = subprocess.run(cmd, capture_output=True, text=True)
            print("🌪️🌪️🌪️ Finished converting")

            # Handling ffmpeg command result
            if result.returncode != 0:
                print(f"Error converting file: {result.stderr}")
                record.status = "failed"
            else:
                record.status = "available"

            record.end_process_date = datetime.now()
            session.commit()

        except Exception as e:
            # Rollback in case of exception
            session.rollback()
            print(f"Exception occurred: {e}")
            if record:
                record.status = "failed"
                session.commit()
        finally:
            print("💥💥💥💥💥💥💥done")
            session.remove()  # Remove session at the end


class ProcesarTarea(Resource):
    def post(self):
        bodyMessage = request.json.get("message").get("data")
        print("🌈🌈🌈🌈🌈", bodyMessage)
        # process_task(app, bodyMessage)
        thread = threading.Thread(
            target=process_task, args=(app, bodyMessage,))
        thread.start()
        return {"mensaje": "Tarea procesada correctamente"}, 200


api.add_resource(ProcesarTarea, '/procesar')
