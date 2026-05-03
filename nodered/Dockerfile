FROM nodered/node-red:latest

# Copiar archivos de configuración
COPY flows.json /data/flows.json
COPY package.json /data/package.json
COPY settings.js /data/settings.js

# Instalar nodos adicionales
WORKDIR /data
RUN npm install

# Puerto que usa Render
ENV PORT=1880

EXPOSE 1880

ENTRYPOINT ["node-red"]
CMD ["--settings", "/data/settings.js", "--userDir", "/data"]