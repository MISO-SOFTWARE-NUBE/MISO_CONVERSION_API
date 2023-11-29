from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
import subprocess
from datetime import datetime
import os
import threading


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
GCP_SUBSCRIPTION_ID = os.getenv("GCP_SUBSCRIPTION_ID", "ConversorTopic-sub")
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
        record = session.query(Solicitudes).get(int(id))

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
        # subprocess.run(cmd)
        print("🌪️🌪️🌪️ Started converting")
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("🌪️🌪️🌪️ Finished converting")
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
        session.rollback()
        print("❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️", e)
        record.status = "failed"
        # raise e
    finally:
        print("💥💥💥💥💥💥💥done")


def post(id):
    thread = threading.Thread(
        target=process_task, args=(id,))
    thread.start()


post(1)
