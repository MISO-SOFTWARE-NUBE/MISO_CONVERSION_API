# MISO_CONVERSION_API

A continuación, se presenta un diagrama que ilustra el diseño de un microservicio destinado a la conversión de formatos de archivos de video. Este servicio cuenta con una serie de endpoints esenciales, los cuales se detallan a continuación:

- /api/auth/signup
- /api/auth/login
- /api/tasks
- /api/tasks/<int:id_task>
- /api/tasks/download_type/<int:id_task>
- /api/tasks

![image](https://github.com/MISO-SOFTWARE-NUBE/MISO_CONVERSION_API/assets/54864717/0ba7d0dc-096f-476b-a423-a5fdc02377b5)

## Proceso de instalación local

- Prerequisitos
  - [Instalacion de docker](https://www.docker.com/get-started/)

- Pasos
  - Clonar el repositorio

  ```sh
  git clone https://github.com/MISO-SOFTWARE-NUBE/MISO_CONVERSION_API.git
  ```

  - Ingresar al repositorio

  ```sh
  cd MISO_CONVERSION_API
  ```

  - Ejecutar comando de compose

  ```sh
  docker-compose up
  ```
  
- Probar con la coleccion de postman suministrada en la [wiki](https://github.com/MISO-SOFTWARE-NUBE/MISO_CONVERSION_API/wiki)

## Proceso de instalación en instancias en plataforma de nube
Hemos creado 2 directorios llamados docker-celery y docker-web. Adentro de dichos directorios se encuentran los archivos de docker-compose correspondientes para correr cada servicio en máquinas independientes. Se espera que adentro de este directorio exista un archivo .env con las siguientes variables que dependerán de su configuración de instancias en la nube:
  
  - DB_HOST
  - DB_DB
  - DB_PORT
  - DB_USER
  - DB_PW
  - BROKER_HOST
  - BROKER_PORT

## Proceso de instalación en instancias en plataforma de nube (entrega 5)
Hemos creado 2 directorios llamados docker-celery-bucket y docker-web-bucket. Adentro de dichos directorios se encuentran los archivos de docker-compose correspondientes para correr cada servicio en máquinas independientes. Se espera que adentro de este directorio exista un archivo .env con las siguientes variables que dependerán de su configuración de instancias en la nube:
- DB_HOST
- DB_DB
- DB_PORT
- DB_USER
- DB_PW
- BROKER_HOST
- BROKER_PORT
- USE_BUCKET
- UPLOAD_BUCKET
