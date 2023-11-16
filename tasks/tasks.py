import os
from celery import Celery
from celery.signals import task_postrun
from datetime import datetime
import subprocess
import tempfile

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from google.cloud import storage
from google.cloud import pubsub_v1

from utils import get_blob_name_from_gs_uri, get_base_file_name

Base = declarative_base()

OUR_HOST = os.getenv("DB_HOST", "localhost")
OUR_DB = os.getenv("DB_DB", "conversiones")
OUR_PORT = os.getenv("DB_PORT", "5432")
OUR_USER = os.getenv("DB_USER", "miso")
OUR_PW = os.getenv("DB_PW", "miso")
OUR_SECRET = os.getenv("SECRET", "conversiones")
OUR_JWTSECRET = os.getenv("JWTSECRET", "conversiones")
USE_PUB_SUB = os.getenv("USE_PUB_SUB", "False").lower() in ('true', '1', 't')
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "crear-proyecto-nuevo-en-gcp")
GCP_TOPIC_ID = os.getenv("GCP_TOPIC_ID", "ConversorTopic")
GCP_SUBSCRIPTION_ID =  os.getenv("GCP_SUBSCRIPTION_ID", "ConversorTopic-sub")
BROKER_HOST = os.getenv("BROKER_HOST", "127.0.0.1")
BROKER_PORT = os.getenv("BROKER_PORT", "6379")
USE_BUCKET = os.getenv("USE_BUCKET", "False").lower() in ('true', '1', 't')
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "miso-converter-flask-app")

SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{}:{}@{}:{}/{}'.format(
    OUR_USER, OUR_PW, OUR_HOST, OUR_PORT, OUR_DB)

# Create Engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=True)

# Session factory
Session = sessionmaker(bind=engine)


class Usuario(Base):
    __tablename__ = 'usuario'

    id = Column(Integer, primary_key=True)
    user = Column(String(128))
    email = Column(String(128))
    password = Column(String(128))

    # Relationship for back-reference from Solicitudes
    solicitudes = relationship("Solicitudes", back_populates="usuario")


class Solicitudes(Base):
    __tablename__ = 'solicitudes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('usuario.id'))
    input_path = Column(String(500))
    output_path = Column(String(500))
    input_format = Column(String(5))
    output_format = Column(String(5))
    fileName = Column(String(500))
    upload_date = Column(DateTime)
    start_process_date = Column(DateTime)
    end_process_date = Column(DateTime)
    status = Column(String(50))

    # Relationship for referencing Usuario
    usuario = relationship("Usuario", back_populates="solicitudes")

def process_task(id):
    # Establish a new session
    session = Session()

    try:
        # 1. Query record in database
        record = session.query(Solicitudes).get(id)

        # 2. Register start_processing_time and update status
        record.start_process_date = datetime.now()
        record.status = "in_process"
        session.commit()

        # Step 3: Conditional logic depending on USE_BUCK env variable
        if USE_BUCKET:
            # Get blob names from db
            input_blob_name = get_blob_name_from_gs_uri(record.input_path)
            output_blob_name = get_blob_name_from_gs_uri(record.output_path)

            # Get gcp blobs for input and output
            input_blob = bucket.blob(input_blob_name)
            output_blob = bucket.blob(output_blob_name)
            print(output_blob_name)

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
                session.commit()
        else:
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
            # subprocess.run(cmd)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(result.stderr)
                print(result.stdout)
                print("Error converting file:", result.stderr)
                record.status = "failed"
            else:
                record.status = "available"
            record.end_process_date = datetime.now()
            session.commit()

    except Exception as e:
        record.status = "failed"
        print(f"An error occurred: {e}")
        session.rollback()  # rollback in case of errors
    finally:
        # Delete the temporary output file after the upload has been attempted
        if os.path.exists(temp_output_file_name):
            os.remove(temp_output_file_name)
        session.close()

if USE_BUCKET:
    client = storage.Client()
    bucket = client.bucket(UPLOAD_BUCKET)

if not USE_PUB_SUB:
    print("Celery is using BROKER_HOST:", BROKER_HOST)
    celery_app = Celery('tasks', broker=f'redis://{BROKER_HOST}:{BROKER_PORT}/0')
    @celery_app.task(name='conversor.convert')
    def perform_task(id):
        process_task(id)
else:
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, GCP_SUBSCRIPTION_ID)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        print(f"Received message: {message}")
        task_id = message.data.decode("utf-8")
        message.ack()
        process_task(task_id)
        print(f"Acknowledged message ID {message.message_id}")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}..\n")

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        subscriber.close()