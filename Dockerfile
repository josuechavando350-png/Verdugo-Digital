FROM node:22-alpine
WORKDIR /app
COPY lib/ ./lib/
COPY stack/catalog.json ./stack/catalog.json
ENV PORT=8177 BIND_ADDRESS=127.0.0.1
USER node
EXPOSE 8177
CMD ["node", "lib/control-plane.mjs"]
