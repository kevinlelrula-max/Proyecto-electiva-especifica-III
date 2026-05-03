FROM nodered/node-red:latest

# Copiar flows y configuración
COPY flows.json /data/flows.json
COPY package.json /data/package.json
COPY settings.js /data/settings.js

# Instalar nodos adicionales
WORKDIR /data
RUN npm install

EXPOSE 1880

CMD ["node-red", "--settings", "/data/settings.js"]