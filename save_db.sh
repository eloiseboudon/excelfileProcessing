#!/bin/bash

# Script de configuration des sauvegardes automatiques
# Usage: ./setup_backup_cron.sh

# Configuration
SCRIPT_DIR="/opt/votre-app"  # Répertoire où se trouvent vos scripts
LOG_DIR="/var/log/ajt-backups"

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Création du répertoire de logs
create_log_directory() {
    if [ ! -d "$LOG_DIR" ]; then
        log "Création du répertoire de logs: $LOG_DIR"
        sudo mkdir -p "$LOG_DIR"
        sudo chown $(whoami):$(whoami) "$LOG_DIR"
    fi
}

# Configuration des tâches cron
setup_cron_jobs() {
    log "Configuration des tâches cron pour les sauvegardes automatiques..."
    
    # Sauvegarde du crontab actuel
    crontab -l > /tmp/current_crontab 2>/dev/null || touch /tmp/current_crontab
    
    # Suppression des anciennes tâches AJT (si elles existent)
    grep -v "ajt.*backup\|AJT.*backup" /tmp/current_crontab > /tmp/new_crontab || touch /tmp/new_crontab
    
    # Ajout des nouvelles tâches
    cat >> /tmp/new_crontab << EOF

# ============ AJT Database Backups ============
# Sauvegarde quotidienne à 02:00
0 2 * * * $SCRIPT_DIR/save_db.sh daily >> $LOG_DIR/backup_daily.log 2>&1

# Sauvegarde hebdomadaire le dimanche à 03:00
0 3 * * 0 $SCRIPT_DIR/save_db.sh weekly >> $LOG_DIR/backup_weekly.log 2>&1

# Sauvegarde mensuelle le 1er de chaque mois à 04:00
0 4 1 * * $SCRIPT_DIR/save_db.sh monthly >> $LOG_DIR/backup_monthly.log 2>&1

# Nettoyage des logs tous les dimanche à 05:00
0 5 * * 0 find $LOG_DIR -name "*.log" -mtime +30 -delete
# ===============================================

EOF
    
    # Installation du nouveau crontab
    crontab /tmp/new_crontab
    
    # Nettoyage
    rm -f /tmp/current_crontab /tmp/new_crontab
    
    log "✅ Tâches cron configurées avec succès!"
}

# Affichage des tâches configurées
show_cron_jobs() {
    log "📅 Tâches cron configurées:"
    echo "----------------------------------------"
    crontab -l | grep -A 10 -B 2 "AJT.*Backup\|ajt.*backup" || echo "Aucune tâche trouvée"
    echo "----------------------------------------"
}

# Création d'un script wrapper pour les logs
create_backup_wrapper() {
    local wrapper_script="$SCRIPT_DIR/backup_wrapper.sh"
    
    log "Création du script wrapper: $wrapper_script"
    
    cat > "$wrapper_script" << 'EOF'
#!/bin/bash

# Wrapper pour les sauvegardes avec gestion des notifications

SCRIPT_DIR="/opt/votre-app"
LOG_DIR="/var/log/ajt-backups"
BACKUP_TYPE="${1:-manual}"

# Fonction pour envoyer des notifications (à adapter)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Exemple avec logger (syslog)
    logger -t "ajt-backup" "$status: $message"
    
    # Exemple avec email (décommentez et adaptez)
    # echo "$message" | mail -s "AJT Backup $status" admin@votre-domaine.com
    
    # Exemple avec webhook Slack (décommentez et adaptez)
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"AJT Backup $status: $message\"}" \
    #   YOUR_SLACK_WEBHOOK_URL
}

# Exécution de la sauvegarde
start_time=$(date)
if $SCRIPT_DIR/save_db.sh "$BACKUP_TYPE"; then
    send_notification "SUCCESS" "Sauvegarde $BACKUP_TYPE terminée avec succès à $(date)"
else
    send_notification "FAILED" "Échec de la sauvegarde $BACKUP_TYPE à $(date)"
fi
EOF
    
    chmod +x "$wrapper_script"
}

# Test des sauvegardes
test_backup() {
    log "🧪 Test de sauvegarde..."
    
    if [ -f "$SCRIPT_DIR/save_db.sh" ]; then
        log "Script de sauvegarde trouvé, test d'exécution..."
        if $SCRIPT_DIR/save_db.sh test_setup; then
            log "✅ Test de sauvegarde réussi!"
        else
            warn "⚠️  Test de sauvegarde échoué, vérifiez la configuration"
        fi
    else
        error "Script save_db.sh introuvable dans $SCRIPT_DIR"
    fi
}

# Configuration des rotations de logs avec logrotate
setup_logrotate() {
    local logrotate_config="/etc/logrotate.d/ajt-backups"
    
    log "Configuration de la rotation des logs..."
    
    sudo tee "$logrotate_config" > /dev/null << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $(whoami) $(whoami)
    postrotate
        # Optionnel: restart d'un service si nécessaire
    endscript
}
EOF
    
    log "✅ Configuration logrotate créée: $logrotate_config"
}

# Menu interactif
show_menu() {
    echo ""
    echo "=== Configuration des sauvegardes automatiques AJT ==="
    echo "1. Configurer les sauvegardes automatiques (cron)"
    echo "2. Afficher les tâches cron actuelles"
    echo "3. Tester une sauvegarde manuelle"
    echo "4. Configurer la rotation des logs"
    echo "5. Installation complète (tout)"
    echo "6. Désinstaller les tâches automatiques"
    echo "0. Quitter"
    echo ""
    read -p "Choisissez une option (0-6): " choice
    
    case $choice in
        1)
            create_log_directory
            setup_cron_jobs
            create_backup_wrapper
            show_cron_jobs
            ;;
        2)
            show_cron_jobs
            ;;
        3)
            test_backup
            ;;
        4)
            setup_logrotate
            ;;
        5)
            create_log_directory
            setup_cron_jobs
            create_backup_wrapper
            setup_logrotate
            test_backup
            show_cron_jobs
            log "🎉 Configuration complète terminée!"
            ;;
        6)
            remove_cron_jobs
            ;;
        0)
            log "Au revoir!"
            exit 0
            ;;
        *)
            warn "Option invalide"
            show_menu
            ;;
    esac
}

# Désinstallation des tâches cron
remove_cron_jobs() {
    log "Suppression des tâches cron AJT..."
    
    crontab -l > /tmp/current_crontab 2>/dev/null || touch /tmp/current_crontab
    grep -v "ajt.*backup\|AJT.*backup" /tmp/current_crontab > /tmp/new_crontab || touch /tmp/new_crontab
    crontab /tmp/new_crontab
    rm -f /tmp/current_crontab /tmp/new_crontab
    
    log "✅ Tâches cron supprimées"
}

# Fonction principale
main() {
    log "🚀 Configuration des sauvegardes automatiques AJT"
    
    # Vérifications
    if [ ! -f "$SCRIPT_DIR/save_db.sh" ]; then
        error "Script save_db.sh introuvable dans $SCRIPT_DIR"
    fi
    
    if [ "$1" = "--auto" ]; then
        # Installation automatique
        create_log_directory
        setup_cron_jobs
        create_backup_wrapper
        setup_logrotate
        log "🎉 Configuration automatique terminée!"
    else
        # Menu interactif
        show_menu
    fi
}

# Exécution
main "$@"