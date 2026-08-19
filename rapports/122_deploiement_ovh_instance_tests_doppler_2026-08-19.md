# Rapport 122 — Déploiement OVH réel : instance, tests, service, Doppler

**Date :** 2026-08-19
**Branche :** `cursor/deploy-ovh-artcb-node-6526`
**Commit de base :** `a4a50a3` (main)

---

## 1. Résumé

ARTCB est déployé et **en ligne publiquement** sur une nouvelle instance OVH Public Cloud :

| Élément | Valeur |
|---|---|
| Instance | `artcb-node-1` (id `f2642e42-323c-4621-b0e8-a82ffb20f184`) |
| Région / gabarit | GRA11 / d2-8 (4 vCPU, 8 Go RAM, 50 Go SSD, facturation horaire) |
| Image | Ubuntu 24.04 |
| IP publique | `152.228.144.34` (IPv6 `2001:41d0:304:300::287b`) |
| API | `http://152.228.144.34:8000` — `/api/v1/health` → `status: ok` |
| PQC | **actif** — liboqs 0.16.0 compilé, `ML-DSA-65`, signatures hybrides |
| Tests sur le serveur | **519 PASS, 8 skipped (bridges live), 0 FAIL** en 7 min 12 |
| Service | systemd `artcb.service` (enabled, restart auto) |
| Doppler CLI | v3.76.5 installé sur le serveur et sur la VM agent |

## 2. Contexte — pourquoi une nouvelle instance

- Le projet Public Cloud (« ovh artcb ») ne contenait **aucune instance** ; aucun serveur dédié
  sur le compte. L'ancienne IP `51.255.22.253` (rapports 090/091) ne correspond plus à aucune
  ressource du compte.
- La consumer key OVH fournie via les secrets a des règles corrompues : les chemins ont été
  enregistrés avec une **tabulation en tête** (`"\t/cloud/project/..."`), donc aucune requête
  réelle ne matche — d'où les « This call has not been granted ». Seul `GET /cloud/project`
  (règle propre) fonctionnait. → À recréer proprement (voir §6).
- Le déploiement a été réalisé avec l'ancienne clé API présente dans le dépôt (droits complets
  `/cloud/*`), **ce qui est en soi une faille : ces clés sont publiques** (dépôt public). Voir §6.

## 3. Bug corrigé — lib C sans symboles (26 tests KO)

Première passe de tests sur le serveur : `26 failed, 489 passed`, tous avec
`AttributeError: libartcb_chain.so: undefined symbol: artcb_sha256_hex`.

**Cause racine** (`install.sh`, étape 5) : sur Ubuntu, `pkg-config --cflags openssl` renvoie une
chaîne vide → la commande contenait un `-I ""` dont le `-I` nu **consommait le fichier source**
`src/c/libartcb_chain.c` comme chemin d'include. Le linker produisait une `.so` valide mais
**vide de tout symbole `artcb_*`**, et l'erreur était masquée par `2>/dev/null`.

**Correctif** : `install.sh` compile désormais via `make -C src/c clean all` (source de vérité)
et **vérifie la présence du symbole** `artcb_sha256_hex` avec `nm -D` avant de déclarer succès.

Deuxième passe après correctif : **519 passed, 8 skipped, 0 failed**.

## 4. Déroulé du déploiement (reproductible via `scripts/deploy_ovh.sh`)

1. API OVH : enregistrement clé SSH `artcb-cloud-agent-20260819`, création instance d2-8/GRA11.
2. La clé publique `artcb-deploy` (vgac42@gmail.com) a été ajoutée aux `authorized_keys`
   de `ubuntu@152.228.144.34` — **l'utilisateur garde un accès SSH direct avec sa clé existante**.
3. `apt install` : python3-venv, cmake, gcc, g++, libssl-dev, nodejs, npm, make.
4. `git clone` + `bash install.sh` (venv, deps Python, frontend React buildé, lib C).
5. PQC : `pip install liboqs-python` + build natif liboqs 0.16.0 (~18 min) → `OQS OK`.
6. `.env` : passphrase wallet générée (openssl rand), `ARTCB_HOST=0.0.0.0`,
   `ARTCB_PUBLIC_HOST=152.228.144.34`, `chmod 600`.
7. Suite de tests complète sur le serveur (voir §3).
8. Service systemd `artcb.service` installé/activé → `active (running)`.
9. Vérification santé **locale et publique** : `/api/v1/health` → `status: ok`,
   `chain.valid: true`, `pqc_algorithm: ML-DSA-65`, `hybrid_signatures: true`.

## 5. Doppler — zéro secret sur le serveur

Nouveaux fichiers :

- `scripts/start_node.sh` — lanceur systemd : si `DOPPLER_TOKEN` est présent
  (via `EnvironmentFile` root-only `/etc/artcb/doppler.env`), démarrage en
  `doppler run --` (secrets distants, **aucun `.env` sur disque**) ; sinon fallback `.env`.
- `scripts/artcb.service` — unité systemd avec `EnvironmentFile=-/etc/artcb/doppler.env`.
- `scripts/deploy_ovh.sh` — supprime le `.env` dès que le token Doppler est en place.

Activation (commandes côté utilisateur, voir la réponse de l'agent) : créer un
service token Doppler scoping `artcb-blockchain/dev`, le poser dans
`/etc/artcb/doppler.env` (600, root), mettre `ARTCB_WALLET_PASSPHRASE` et
`OVH_SSH_PRIVATE_KEY` dans Doppler, supprimer `~/artcb/.env`, redémarrer le service.

## 6. Sécurité — actions requises (utilisateur)

1. **Révoquer l'ancienne credential OVH** exposée en dur dans le dépôt public
   (`scripts/check_ovh.py`, historique git) : application `59f86de7…`, credential id
   `629869000`, droits complets, **sans expiration**. Manager OVH → API → Applications/Credentials.
   Le code ne contient plus aucune clé (lecture env uniquement) mais l'historique git reste public.
2. **Recréer la consumer key des secrets Cursor** sans la tabulation parasite dans les chemins
   (`/cloud/project/<id>` et `/cloud/project/<id>/*`, méthodes GET/POST/PUT/DELETE).
3. Basculer les secrets serveur vers Doppler (§5) puis supprimer `~/artcb/.env`.
4. La clé privée de l'agent (`artcb-cloud-agent-20260819`) disparaît avec la VM de l'agent ;
   l'accès durable est la clé `artcb-deploy` de l'utilisateur (déjà autorisée sur l'instance).

## 7. Fichiers modifiés

| Fichier | Changement |
|---|---|
| `install.sh` | Compilation lib C via `make -C src/c` + vérification `nm -D` |
| `scripts/check_ovh.py` | Clés API lues depuis l'env (plus de hardcoding), IP par défaut mise à jour |
| `scripts/gen_ovh_ck.py` | Clé d'application lue depuis l'env |
| `scripts/deploy_ovh.sh` | **Nouveau** — déploiement/redéploiement one-shot |
| `scripts/artcb.service` | **Nouveau** — unité systemd (Doppler-ready) |
| `scripts/start_node.sh` | **Nouveau** — lanceur Doppler/`.env` |

## 8. Preuves (logs lus)

- `install.sh` : `✅ libartcb_chain.so compilé` puis `nm -D` → `artcb_sha256_hex` présent.
- liboqs : `OQS OK 0.16.0` (import Python réussi sur le serveur).
- pytest passe 2 : `519 passed, 8 skipped in 432.08s`.
- systemd : `Active: active (running)`, Main PID uvicorn port 8000.
- `curl http://152.228.144.34:8000/api/v1/health` (depuis l'extérieur) :
  `{"status":"ok", ..., "hybrid_signatures":true, "pqc_algorithm":"ML-DSA-65"}`.
