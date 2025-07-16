# Étape 1 : Build React
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Étape 2 : Serve statique avec NGINX
FROM nginx:stable-alpine

# Supprimer le site par défaut de nginx
RUN rm -rf /usr/share/nginx/html/*

# Copier le build React vers nginx
COPY --from=builder /app/build /usr/share/nginx/html

# Copier la config nginx personnalisée (si besoin)
# COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]