# Workflow Claude Code Optimal pour AJT PRO

Guide de bonnes pratiques pour développer efficacement avec Claude Code. Priorise **la vélocité** et **l'efficacité token**.

---

## 📋 Quick Reference

### Scénarios courants

| Scénario | Commandes | Tokens | Temps |
|---|---|---|---|
| Fix bug simple | `git add . && git commit -m "fix:..."` + `git push` | 50 | 30 sec |
| Feature avec tests | `/clean-commit` + `git push` | 200-300 | 1 min |
| Feature sensible, vérifier CI | `/push-and-wait` | 500-800 | 5-10 min |
| Full workflow (rare) | `/full-deploy` | 100 | 10 sec (async) |
| Code review avant commit | `/review` (haiku) + `/clean-commit` | 300 | 2 min |

**Rule of thumb** : 90% des jours, utilise **`/clean-commit` + `git push`**. C'est ça le workflow standard.

---

## 🚀 Workflows détaillés

### Workflow 1 : Daily routine (90% du temps)

**Cas** : Tu as modifié des fichiers, testé localement, prêt à pousser.

```bash
# 1. Clean & commit atomique
/clean-commit

# 2. Push
git push origin dev

# 3. Quitter. Les webhooks GitHub font :
#    - CI runs (2-5 min) — tu reçois une notification
#    - Si CI ✅ → merge auto de dev vers main
#    - Si main merge → deploy VPS auto (webhook)
#    - Toi : retour à l'éditeur, next issue
```

**Tokens** : ~200-300
**Temps total** : 1 min (toi) + 5-10 min (async)
**Attente** : 0 sec (tu quittes)

---

### Workflow 2 : Vérify before merge (quand tu es prudent)

**Cas** : Feature complexe, tu veux **vraiment** vérifier que CI passe avant merge.

```bash
# 1. Clean & commit
/clean-commit

# 2. Push + surveillance CI (polling synchrone)
/push-and-wait

# Le skill :
#  - Pousse le code
#  - Crée PR si besoin
#  - Affiche PR link
#  - Attend CI (watch) → logs en temps réel
#  - Si passe → Merge auto + info deploy
#  - Si échoue → Logs + diagnosis, STOP

# 3. Que faire après :
#    ✅ Si passe → Déjà mergé, déployé en background
#    ❌ Si échoue → Fix code local + git push (nouveau commit)
```

**Tokens** : ~500-800
**Temps total** : 5-10 min (toi attends)
**Bonus** : Tu vois les logs CI en temps réel

---

### Workflow 3 : Code review avant commit (sécurité)

**Cas** : Code sensible (auth, matching LLM) — veux review avant commit.

```bash
# 1. Review les changements (Haiku = pas cher)
/model haiku
/review

# Haiku revient avec :
#  - Code mort à nettoyer ?
#  - Security issues ?
#  - Style problems ?

# 2. Fix issues identifiées
# (Edit files, apply suggestions)

# 3. Clean commit (inclut les fixes)
/clean-commit

# 4. Push
git push origin dev
```

**Tokens** : ~300-400 (haiku cheap)
**Temps total** : 2-3 min
**Bénéfice** : Zéro regrets après push

---

### Workflow 4 : Emergency hotfix (production urgence)

**Cas** : Bug en prod, faut déployer ASAP.

```bash
# 1. Fix rapide
# (Pas de tests exhaustifs, just fix)

# 2. Commit direct
git add <files>
git commit -m "fix(scope): urgent hotfix description"

# 3. Push DIRECT sur main (!)
git push origin main

# GitHub Actions webhook :
#  - CI runs
#  - Si passe → Deploy immédiat via VPS
#  - ~2-3 min production

# 4. Communique à l'équipe sur Slack
```

**Tokens** : 0 (pas de Claude)
**Temps total** : 2 min (toi) + 5 min (CI/deploy)
**⚠️ Attention** : Pas de PR review. À utiliser TRÈS rarement.

---

## ⚡ Skills optimisés pour le workflow

### `/clean-commit` — Tous les jours
```
Scanne debug code + nettoie + commit atomique.
C'est ta macro pre-commit standard.
```

**Quand** : Avant chaque `git push`
**Coût** : ~200 tokens
**Output** : 1+ commits propres

---

### `/push-and-wait` — Quand tu doutes de la CI
```
Push + poll CI jusqu'à fini + merge auto si ✅
```

**Quand** : Feature sensible, refactor big, doute sur tests
**Coût** : ~500-800 tokens (dépend durée CI)
**Output** : Merged + deployed ou erreurs CI détaillées

---

### `/full-deploy` — Presque jamais
```
Clean commit + push (async).
Utilise les webhooks, pas de polling.
```

**Quand** : Code ready à pousser, pas envie d'attendre
**Coût** : ~100 tokens
**Output** : Push fait, GitHub gère le reste

---

### `/review` (Haiku) — Code sensible
```
Scan rapide : dead code, logs, security, style.
Très cheap avec Haiku (1/5 du prix Sonnet).
```

**Quand** : Avant `/clean-commit` si doute
**Coût** : ~100-150 tokens (haiku)
**Output** : Points d'amélioration, prêt pour commit

---

## 📊 Token budget par jour

**Budget par dev** : ~1000-1500 tokens/jour (Claude Code tier standard)

### Allocation example
```
50% : Daily commits/pushes (5-10 x 200 tokens = ~1000)
20% : Code reviews (2-3 x 150 tokens haiku = 300-450)
20% : Debugging sur test/CI (2-3 x 200 = 400-600)
10% : Exploration/research (1 x 100-200)
```

**Rule** : Si une session dépasse ~500 tokens sans résultat, **stop et redémarrer** avec `/clear` + `/catchup` pour compacter.

---

## ❌ Quoi éviter

| ❌ Mauvais | ✅ Bon | Raison |
|---|---|---|
| Appeler `/full-deploy` 10x/jour | Utiliser `/clean-commit` + push | Async webhooks font le travail |
| Attendre polling CI sans raison | Utiliser `/push-and-wait` juste si prudent | 5+ min attendus pour rien |
| `/review` avec Sonnet/Opus | `/review` avec Haiku | Code review = pas besoin reasoning |
| Push sans clean-commit | Lancer `/clean-commit` d'abord | Garder repo propre |
| Git push et workflow complet manual | Utiliser skills pour automation | Trop verbeux, trop d'erreurs |

---

## 🔗 GitHub Actions webhooks (background)

Une fois code pushé, GitHub Actions se déclenche **automatiquement** :

```
Push event
  ↓
.github/workflows/ci.yml runs
  ├─ Tests (pytest + vitest)
  ├─ Linter (eslint)
  └─ Build check
  ↓
If CI passes
  ├─ Auto-merge dev → main (règles github)
  └─ On main push → deploy.yml runs
     ├─ SSH to VPS
     ├─ docker compose pull + restart
     ├─ migrations alembic
     └─ health checks
```

**Tu reçois notifications** via GitHub — peux ignorer jusqu'à vérification.

---

## 📋 Checklist pre-push

Avant chaque `/clean-commit` :

```
☐ Code builds locally
☐ Tests pass locally (`npm test`, `pytest tests/`)
☐ No console.log / print() left
☐ No debug flags (DEBUG = true)
☐ No commented code
☐ .env, credentials pas stagées
☐ Commit message en Conventional Commits
```

**Result** : Push qui passe CI à 99%.

---

## 🎯 Optimisations futures

Si tu veux aller plus loin :

- **Husky hooks** : Pré-push hooks qui run tests auto
- **Lint-staged** : Lint seulement les fichiers stagés (faster)
- **GitHub branch protection** : Force PR review avant merge (slow mais safe)
- **Scheduled nightly tests** : Run tests longs en background la nuit

Mais pour maintenant : **`/clean-commit` + `git push` × N** = 80% des cas.

---

## 📞 Questions

### Q: Combien de temps avant que mon code soit en prod ?
**A** : ~5-10 min après push (CI 2-5 min + deploy 2-3 min).

### Q: Et si CI échoue ?
**A** : Notification GitHub + utilise `/fix-pipeline` pour debug, fix local, re-push.

### Q: Peux-je push direct sur main ?
**A** : ✅ Oui (hotfix). Mais la règle = dev → main via PR (fait par webhook).

### Q: Les webhooks sont fiables ?
**A** : ✅ Oui (GitHub garantit). Vérifie sur GitHub Actions dashboard si doute.

### Q: Comment revenir en arrière si deploy casse prod ?
**A** : `git revert <hash>` + push. Deploy auto pré-précédent état. ~5 min rollback.
