---
name: Traçabilité des démarrages
description: Règle durable pour reconstituer une tentative de démarrage et un incident healthcheck.
---

Le démarrage doit créer son journal avant toute étape fonctionnelle et conserver un identifiant unique partagé par le shell, les logs Python, Uvicorn et les accès HTTP.

**Why:** Les incidents healthcheck peuvent survenir avant que l’application soit prête. Un journal applicatif initialisé tardivement ne permet pas de distinguer une erreur de supervision, d’import, d’initialisation ou de route.

**How to apply:** Lors de toute modification du démarrage ou du logging, préserver le fichier de run shell, le JSONL centralisé, les PID, les codes de sortie, les tâches arrière-plan et la preuve `Application startup complete` avant de conclure sur un healthcheck.