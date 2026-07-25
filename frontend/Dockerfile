FROM node:18-alpine

WORKDIR /app

# Layer 1: dependencies — cached unless package.json changes
COPY package*.json ./
RUN npm install

# Layer 2: source — cached unless frontend code changes
COPY . .

# Layer 3: webpack build — cached unless source changes
# PORTAL and REACT_APP_API_URL are set per-service in docker-compose build args
ARG PORTAL=b2b
ARG REACT_APP_API_URL=http://localhost:8080
ENV PORTAL=$PORTAL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

RUN npm run build:${PORTAL}

EXPOSE 3000 3001 3002

# Instant startup — just serves the pre-built static dist
CMD npx -y serve -s dist/${PORTAL} -l ${PORT:-3000}
