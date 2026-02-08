FROM node:lts-alpine

ENV NODE_ENV=development
WORKDIR /usr/src/app

COPY ["package.json", "package-lock.json*", "npm-shrinkwrap.json*", "./"]
RUN npm ci --silent && mv node_modules ../

COPY . .

RUN chown -R node /usr/src/app

USER node

CMD ["npm", "run", "dev"]
