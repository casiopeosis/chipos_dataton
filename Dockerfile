# Servidor estático del frontend (sin build). Los datos (data/outputs, data/reference)
# se montan en tiempo de ejecución vía docker-compose.yml, no se copian en la imagen:
# así cualquier cambio en esos archivos se refleja al reiniciar el contenedor sin rebuild.
FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY frontend /usr/share/nginx/html

EXPOSE 80
