import os
from datetime import timedelta

OUR_HOST = os.getenv("DB_HOST", "localhost")
OUR_DB = os.getenv("DB_DB", "conversiones")
OUR_PORT = os.getenv("DB_PORT", "5432")
OUR_USER = os.getenv("DB_USER", "miso")
OUR_PW = os.getenv("DB_PW", "miso")
OUR_SECRET = os.getenv("SECRET", "conversiones")
OUR_JWTSECRET = os.getenv("JWTSECRET", "conversiones")

DEBUG = False
SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{OUR_USER}:{OUR_PW}@{OUR_HOST}:{OUR_PORT}/{OUR_DB}'
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = OUR_JWTSECRET
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
SECRET_KEY = OUR_SECRET
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static', 'uploads')
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "miso-converter-flask-app")
BROKER_HOST = os.getenv("BROKER_HOST", "127.0.0.1")
BROKER_PORT = os.getenv("BROKER_PORT", "6379")
PROPAGATE_EXCEPTIONS = True
USE_BUCKET = os.getenv("USE_BUCKET", "False").lower() in ('true', '1', 't')
USE_PUB_SUB = os.getenv("USE_PUB_SUB", "False").lower() in ('true', '1', 't')
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "crear-proyecto-nuevo-en-gcp")
GCP_TOPIC_ID = os.getenv("GCP_TOPIC_ID", "ConversorTopic")
GCP_SUBSCRIPTION_ID =  os.getenv("GCP_SUBSCRIPTION_ID", "ConversorTopic-sub")
