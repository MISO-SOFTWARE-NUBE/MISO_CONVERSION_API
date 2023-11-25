from ..models import db, Solicitudes, Usuario
from utils import get_base_file_name, get_file_extension, map_db_request, get_blob_name_from_gs_uri
import hashlib
import json
import os
from datetime import datetime
from flask import request, current_app, send_file
from werkzeug.utils import secure_filename
from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from flask_restful import Api
from celery import Celery
from config import BROKER_HOST, BROKER_PORT, USE_BUCKET, UPLOAD_BUCKET, USE_PUB_SUB, GCP_PROJECT_ID, GCP_SUBSCRIPTION_ID, GCP_TOPIC_ID
from google.cloud import storage
from google.cloud import pubsub_v1


if USE_PUB_SUB:
    publisher = pubsub_v1.PublisherClient()
    topic_name = f'projects/{GCP_PROJECT_ID}/topics/{GCP_TOPIC_ID}'

    def publish_to_topic(id):
        data = str(id).encode("utf-8")
        future = publisher.publish(topic_name, data)
        print(f"Published message id {future.result()}")
else:
    celery_app = Celery(
        'tasks', broker=f'redis://{BROKER_HOST}:{BROKER_PORT}/0')

    @celery_app.task(name='conversor.convert')
    def perform_task(id):
        pass

if USE_BUCKET:
    client = storage.Client()
    bucket = client.bucket(UPLOAD_BUCKET)


class VistaSignUp(Resource):
    def post(self):

        campos = {
            "user": request.json.get("user"),
            "email": request.json.get("email"),
            "password": request.json.get("password"),
        }

        for nombre_campo, valor in campos.items():
            if valor is None:
                return {'message': f"Campo {nombre_campo} requerido"}, 400

        user, email, password = campos.values()

        usuario_existente = Usuario.query.filter(
            Usuario.user == user or Usuario.email == email).first()
        if usuario_existente is None:
            encrypted_password = hashlib.md5(
                password.encode('utf-8')).hexdigest()
            new_user = Usuario(
                user=user, password=encrypted_password, email=email)
            db.session.add(new_user)
            db.session.commit()
            return {"mensaje": "Usuario creado exitosamente", "id": new_user.id}, 200
        else:
            return {"mensaje": "El usuario ya existe"}, 404


class VistaLogIn(Resource):
    def post(self):
        campos = {
            "user": request.json.get("user"),
            "password": request.json.get("password"),
        }

        for nombre_campo, valor in campos.items():
            if valor is None:
                return {'message': f"Campo {nombre_campo} requerido"}, 400

        user, password = campos.values()

        encrypted_password = hashlib.md5(
            password.encode('utf-8')).hexdigest()
        user = Usuario.query.filter(
            Usuario.user == user, Usuario.password == encrypted_password).first()
        if user is None:
            return {"mensaje": "Usuario o contraseña erroneos"}, 404
        else:
            access_token = create_access_token(identity=user.id)
            return {"mensaje": "Inicio de sesión exitoso", "token": access_token}


class VistaSolicitud(Resource):
    @jwt_required()
    def get(self, download_type, id_task):
        if id_task is None:
            return {'message': 'Debe enviar un id de solicitud para descargar el archivo'}, 400
        db_request = Solicitudes.query.filter(
            Solicitudes.id == id_task).first()
        user_id = get_jwt_identity()
        if db_request is None:
            return {'message': 'Solicitud no encontrada'}, 404
        if user_id != db_request.user_id:
            return {'message': 'El recurso solicitado no le pertenece'}, 404
        # Verifica que el archivo este disponible
        if db_request.status != 'available' and download_type == 'converted':
            if db_request.status == 'failed':
                return {'message': 'Ocurrió un error en la conversión de su archivo'}, 400
            return {'message': 'Su archivo aun no esta listo, por favor intente mas tarde'}, 400
        if USE_BUCKET:
            if download_type == 'original':
                blob_path = get_blob_name_from_gs_uri(db_request.input_path)
            elif download_type == 'converted':
                blob_path = get_blob_name_from_gs_uri(db_request.output_path)
            else:
                return {'message': 'Debe escoger el origen del archivo (original/converted)'}, 400
            public_url = f"https://storage.googleapis.com/{UPLOAD_BUCKET}/{blob_path}"
            return {'download_url': public_url}, 200
        else:
            # Descarga el archivo (original/converted) del servidor
            if download_type == 'original':
                destination_path = f"{db_request.input_path}/{db_request.fileName}.{db_request.input_format}"
            elif download_type == 'converted':
                destination_path = f"{db_request.output_path}/{db_request.fileName}.{db_request.output_format}"
            else:
                return {'message': 'Debe escoger el origen del archivo (original/converted)'}, 400
            return send_file(destination_path, as_attachment=True)

    @jwt_required()
    def delete(self, id_task):
        if id_task is None:
            return {'message': 'Debe enviar un id de solicitud para borrar'}, 400
        db_request = Solicitudes.query.filter(
            Solicitudes.id == id_task).first()
        user_id = get_jwt_identity()
        if db_request is None:
            return {'message': 'Solicitud no encontrada'}, 404
        if user_id != db_request.user_id:
            return {'message': 'El recurso solicitado no le pertenece'}, 404
        if USE_BUCKET:
            # Get and delete input and output blobs
            input_blob_name = get_blob_name_from_gs_uri(db_request.input_path)
            input_blob = bucket.blob(input_blob_name)
            if input_blob.exists():
                input_blob.delete()

            output_blob_name = get_blob_name_from_gs_uri(
                db_request.output_path)
            output_blob = bucket.blob(output_blob_name)
            if output_blob.exists():
                output_blob.delete()
        else:
            input_file_to_delete = f"{db_request.input_path}/{db_request.fileName}.{db_request.input_format}"
            if os.path.exists(input_file_to_delete):
                os.remove(input_file_to_delete)
            output_file_to_delete = f"{db_request.output_path}/{db_request.fileName}.{db_request.output_format}"
            if os.path.exists(output_file_to_delete):
                os.remove(output_file_to_delete)
        db.session.delete(db_request)
        db.session.commit()
        return {'message': 'Solicitud eliminada'}, 200


class VistaSolicitudes(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        db_request = Solicitudes.query.filter(
            Solicitudes.user_id == user_id).all()
        mapr_result = map(map_db_request, db_request)
        list_result = list(mapr_result)
        return list_result

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        if user_id is None:
            return {'message': 'Debe enviar un token valido para poder asociar la solicitud'}, 400
        print("request: ", request)
        print("request.files: ", request.files)
        print("request.files.file: ", request.files.get('file'))
        print("request.form.output_format: ",
              request.form.get('output_format'))
        file = request.files.get('file')
        if file is None:
            return {'message': 'Debe enviar un archivo para convertir'}, 400

        output_format = request.form.get('output_format')
        if not output_format:
            return {'message': 'Debe enviar el formato de salida deseado'}, 400

        logged_user = Usuario.query.get(user_id)
        filename = secure_filename(file.filename)
        input_format = get_file_extension(filename)

        # Step 0: validate formats
        valid_formats = ('mp4', 'webm', 'avi', 'mpg', 'wmv')
        if input_format not in valid_formats:
            return {'message': 'Formato de archivo de entrada invalido'}, 400
        if output_format not in valid_formats:
            return {'message': 'Formato de archivo de salida invalido'}, 400
        if input_format == output_format:
            return {'message': 'Los formatos de archivo no pueden ser iguales'}, 400

        # Step 1: with timestamp, construct the paths
        now = datetime.now()
        current_time = now.strftime("%Y%m%d%H%M%S%f")[:-3]

        # Step 2: Upload file based on USE_BUCKET env variable
        if USE_BUCKET:
            input_blob = bucket.blob(
                f'{logged_user.user}/input/{current_time}/{filename}')
            input_blob.upload_from_string(
                file.read(), content_type=file.content_type)
            output_blob = bucket.blob(
                f'{logged_user.user}/output/{current_time}/{get_base_file_name(filename)}.{output_format}')
        else:
            input_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], logged_user.user, 'input', str(current_time))
            output_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], logged_user.user, 'output', str(current_time))

            # Check directory existence and save file
            if not os.path.exists(input_path):
                os.makedirs(input_path)
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            file.save(os.path.join(input_path, filename))

        # Step 3: Create the Solicitudes entry without paths first
        new_request = Solicitudes(
            user_id=user_id,
            input_path=input_path if not USE_BUCKET else f'gs://{bucket.name}/{input_blob.name}',
            output_path=output_path if not USE_BUCKET else f'gs://{bucket.name}/{output_blob.name}',
            fileName=get_base_file_name(filename),
            upload_date=datetime.now(),
            status='uploaded',
            output_format=output_format,
            input_format=input_format
        )
        db.session.add(new_request)
        db.session.commit()

        # Proceed with the queue
        if USE_PUB_SUB:
            publish_to_topic(new_request.id)
        else:
            args = (new_request.id, )
            perform_task.apply_async(args)

        return {'message': f'Solicitud registrada, para consultar su archivo utilice el siguiente id: ({new_request.id})'}, 200
