---
name: Démarrage PQC différé
description: Contrainte de démarrage pour liboqs-python et mode bootstrap ARTCB.
---

Le démarrage ARTCB doit rester disponible même si `liboqs-python` est installé
sans sa bibliothèque native `liboqs.so`. Une vérification native préalable doit
éviter tout import `oqs` susceptible de lancer une compilation automatique
bloquante. Dans ce cas, l’API démarre avec un fallback cryptographique explicite
et expose son statut dans `/health`.

**Why:** l’import synchrone de `oqs` a déjà empêché Uvicorn d’ouvrir le port
attendu par le healthcheck Replit.

**How to apply:** conserver la compilation PQC en arrière-plan ; ne jamais la
mettre sur le chemin critique de la création FastAPI. En mode bootstrap, servir
le frontend et ses assets, mais laisser les routes métier protégées jusqu’à
l’initialisation de l’identité du nœud.