# ---- Build stage ----
FROM node:20-slim AS builder

# Declare build arg so docker-compose can pass VITE_BACKEND_URL.
# Vite bakes VITE_* vars into the bundle at build time.
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

WORKDIR /app

# Install yarn and dependencies first (better layer caching)
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# Copy source and build
COPY . .
RUN yarn build

# ---- Serve stage ----
FROM nginx:1.27-alpine

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Nginx config: serve SPA, proxy /api and /v1 to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
