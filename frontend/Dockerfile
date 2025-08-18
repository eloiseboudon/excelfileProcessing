# Étape 1 : Build React avec gestion des erreurs Rollup
FROM node:20-bullseye AS builder

WORKDIR /app

# Installer les dépendances système pour le diagnostic
RUN apt-get update && apt-get install -y tree && rm -rf /var/lib/apt/lists/*

# Variable de build pour l'URL de l'API
ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}

# Variable pour forcer l'utilisation de la version JS de Rollup si nécessaire
ENV ROLLUP_FORCE_JS=1

# Copier les fichiers package
COPY package*.json ./

# Installation avec gestion d'erreurs Rollup
RUN echo "=== Installation des dépendances ===" && \
    npm install --omit=optional || \
    (echo "Première installation échouée, nettoyage et retry..." && \
    rm -rf node_modules package-lock.json && \
    npm cache clean --force && \
    npm install --legacy-peer-deps --omit=optional) || \
    (echo "Deuxième tentative avec --force..." && \
    npm install --force --omit=optional)

# Réinstaller esbuild proprement
RUN npm uninstall esbuild && npm install esbuild

# Installation spécifique de Rollup si le module natif pose problème
RUN npm list @rollup/rollup-linux-x64-gnu || \
    (echo "Module natif Rollup manquant, installation manuelle..." && \
    npm install @rollup/rollup-linux-x64-gnu --save-dev) || \
    (echo "Installation du module natif échouée, forçage de la version JS" && \
    export ROLLUP_FORCE_JS=1)

RUN chmod +x ./node_modules/.bin/vite

# Copier le code source
COPY . .

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
    cat vite.config.js 2>/dev/null || cat vite.config.ts 2>/dev/null || echo "vite.config non trouvé" && \
    echo "=== Vérification des modules Rollup ===" && \
    ls -la node_modules/@rollup/ 2>/dev/null || echo "Modules Rollup non trouvés"

# Build de l'application avec gestion d'erreurs
RUN echo "=== Tentative de build principal ===" && \
    npm run build || \
    (echo "Build échoué, tentative avec ROLLUP_FORCE_JS..." && \
    export ROLLUP_FORCE_JS=1 && npm run build) || \
    (echo "Deuxième tentative échouée, réinstallation de Rollup..." && \
    npm install rollup@3.29.4 --save-dev --legacy-peer-deps && \
    npm run build) || \
    (echo "Tentative avec downgrade de Vite..." && \
    npm install vite@4.5.3 --save-dev --legacy-peer-deps && \
    npm run build) || \
    (echo "ERREUR: Toutes les tentatives de build ont échoué" && exit 1)

# Diagnostic après le build
RUN echo "=== Contenu après build ===" && \
    ls -la && \
    echo "=== Recherche des dossiers de build ===" && \
    find . -type d -name "build" -o -name "dist" && \
    echo "=== Contenu du dossier de sortie ===" && \
    (ls -la build/ 2>/dev/null && echo "Build trouvé dans build/") || \
    (ls -la dist/ 2>/dev/null && echo "Build trouvé dans dist/") || \
    (echo "ERREUR: Aucun dossier de build trouvé" && exit 1) && \
    echo "=== Vérification des fichiers essentiels ===" && \
    (test -f build/index.html && echo "✅ index.html présent") || \
    (test -f dist/index.html && echo "✅ index.html présent dans dist") || \
    (echo "⚠️ index.html manquant" && find . -name "index.html" -type f)

# Étape 2 : Serve statique avec NGINX
FROM nginx:stable-alpine

# Supprimer le site par défaut de nginx
RUN rm -rf /usr/share/nginx/html/*

# Copier le build React vers nginx
COPY --from=builder /app/build /usr/share/nginx/html/

# Copier la config nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

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

# Vérification finale que les fichiers sont bien copiés
RUN echo "=== Vérification finale du contenu nginx ===" && \
    ls -la /usr/share/nginx/html/ && \
    test -f /usr/share/nginx/html/index.html && echo "✅ Frontend prêt" || \
    (echo "❌ index.html manquant dans nginx" && exit 1)

USER nextjs

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]