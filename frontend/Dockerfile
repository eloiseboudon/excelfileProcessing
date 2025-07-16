# Étape 1 : Build React
FROM node:20-alpine AS builder

WORKDIR /app

# Installer les dépendances système pour le diagnostic
RUN apk add --no-cache tree

# Variable de build pour l'URL de l'API
ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}

# Copier les fichiers package
COPY frontend/package*.json ./

# Installer les dépendances (toutes les dépendances pour pouvoir build)
RUN npm install

# Copier le code source
COPY frontend/ .

# Diagnostic de la structure avant le build
RUN echo "=== Structure du projet ===" && \
    ls -la && \
    echo "=== Contenu du dossier src ===" && \
    ls -la src/ 2>/dev/null || echo "Dossier src/ non trouvé" && \
    echo "=== Recherche d'index.html ===" && \
    find . -name "index.html" -type f || echo "index.html non trouvé" && \
    echo "=== Contenu de index.html ===" && \
    cat index.html 2>/dev/null || echo "index.html non lisible" && \
    echo "=== Vérification de la config Vite ===" && \
    cat vite.config.js 2>/dev/null || cat vite.config.ts 2>/dev/null || echo "vite.config non trouvé"

# Build de l'application
RUN npm run build

# Diagnostic après le build
RUN echo "=== Contenu après build ===" && \
    ls -la && \
    echo "=== Recherche des dossiers de build ===" && \
    find . -type d -name "build" -o -name "dist" && \
    echo "=== Contenu du dossier de sortie ===" && \
    ls -la dist/ 2>/dev/null || ls -la build/ 2>/dev/null || echo "Aucun dossier de build trouvé"

# Étape 2 : Serve statique avec NGINX
FROM nginx:stable-alpine

# Supprimer le site par défaut de nginx
RUN rm -rf /usr/share/nginx/html/*

# Copier le build React vers nginx (Vite génère dans dist/ par défaut)
# Vite place le résultat du build dans le dossier "build" (voir outDir de
# vite.config.ts). On le copie donc vers le dossier servi par nginx.
COPY --from=builder /app/build /usr/share/nginx/html

# Copier la config nginx personnalisée
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Créer un utilisateur non-root pour la sécurité
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Changer les permissions
RUN chown -R nextjs:nodejs /usr/share/nginx/html
RUN chown -R nextjs:nodejs /var/cache/nginx
RUN chown -R nextjs:nodejs /var/log/nginx
RUN chown -R nextjs:nodejs /etc/nginx/conf.d
RUN touch /var/run/nginx.pid
RUN chown -R nextjs:nodejs /var/run/nginx.pid

USER nextjs

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
