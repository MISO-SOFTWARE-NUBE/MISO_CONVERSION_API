import os
from datetime import datetime
import subprocess
import tempfile
import base64

from flask import request, current_app
from flask_cors import CORS
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource
from google.cloud import storage

from src_worker import create_app
from utils import get_blob_name_from_gs_uri


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

client = storage.Client()
bucket = client.bucket(current_app.config['UPLOAD_BUCKET'])


def process_task(id):
    try:
        # 1. Query record in database
        record = db.session.query(Solicitudes).get(id)

        # 2. Register start_processing_time and update status
        record.start_process_date = datetime.now()
        record.status = "in_process"
        db.session.commit()

        # 3. Get blob names from db
        input_blob_name = get_blob_name_from_gs_uri(record.input_path)
        output_blob_name = get_blob_name_from_gs_uri(record.output_path)

        # Get gcp blobs for input and output
        input_blob = bucket.blob(input_blob_name)
        output_blob = bucket.blob(output_blob_name)

        # Download the input file to a temp file
        with tempfile.NamedTemporaryFile() as temp_input_file:
            input_blob.download_to_filename(temp_input_file.name)
            fd_out, temp_output_file_name = tempfile.mkstemp(
                suffix=f'.{record.output_format}')
            os.close(fd_out)

            cmd = [
                'ffmpeg',
                '-y',
                '-f', record.input_format,
                '-i', temp_input_file.name,
                temp_output_file_name
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print("Error converting file:",
                      result.stderr, result.stdout)
                record.status = "failed"
            else:
                if os.path.getsize(temp_output_file_name) > 0:
                    with open(temp_output_file_name, 'rb') as temp_output_file:
                        output_blob.upload_from_file(
                            temp_output_file, content_type=f'video/{record.output_format}')
                    record.status = "available"
                else:
                    print("Conversion resulted in an empty file.")
                    record.status = "failed"

            # Update the end process date and commit the status
            record.end_process_date = datetime.now()
            db.session.commit()
    except Exception as e:
        db.session.rollback()  # rollback in case of errors
        record.status = "failed"
        raise e
    finally:
        # Delete the temporary output file after the upload has been attempted
        if os.path.exists(temp_output_file_name):
            os.remove(temp_output_file_name)


class ProcesarTarea(Resource):
    def post(self):
        print(request.json)
        bodyMessage = request.json.get("message").get("data")
        bodyText = base64.b64decode(bodyMessage)
        print(bodyText)
        id = str(bodyText)
        try:
            process_task(id)
            return {"mensaje": "Tarea procesada correctamente"}, 200
        except Exception as e:
            return {"mensaje": "Ocurrió un error procesando la tarea"}, 404


api.add_resource(ProcesarTarea, '/procesar')
