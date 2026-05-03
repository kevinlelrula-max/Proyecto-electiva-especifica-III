FROM nodered/node-red:latest

COPY flows.json /data/flows.json
COPY flows_cred.json /data/flows_cred.json
COPY package.json /data/package.json
COPY settings.js /data/settings.js

WORKDIR /data
RUN npm install

ENV PORT=1880

EXPOSE 1880

ENTRYPOINT ["node-red"]
CMD ["--settings", "/data/settings.js", "--userDir", "/data"]