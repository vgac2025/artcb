# Rapport 123 — Rotation clés OVH, bascule Doppler complète, tests finaux

**Date :** 2026-08-19
**Branche :** `cursor/deploy-ovh-artcb-node-6526`
**Suite du rapport :** 122 (déploiement instance `artcb-node-1`)

---

## 1. Résumé — état final

| Vérification | Résultat |
|---|---|
| Service `artcb.service` | `active` (systemd, restart auto, mode `doppler run`) |
| API publique | `http://152.228.144.34:8000/api/v1/health` → `status: ok` |
| PQC | `ML-DSA-65`, `hybrid_signatures: true`, `chain.valid: true` |
| Tests (mode Doppler, sur le serveur) | **519 PASS, 8 skipped (bridges live), 0 FAIL** — 7 min 14 |
| Secrets sur le serveur | **Aucun** — `.env` détruit (`shred`), wallet chiffré via passphrase Doppler |
| Seul résidu sur disque | `/etc/artcb/doppler.env` (token service Doppler, root, `-rw-------`, révocable) |
| Clé API OVH exposée (dépôt public) | **RÉVOQUÉE et vérifiée morte** |
| Clés API OVH corrompues (tabulation) | **RÉVOQUÉES** |
| Nouvelle clé API OVH | Validée, règles propres, scopée projet, sans expiration |

## 2. Rotation des credentials API OVH

### Problème initial (rappel rapport 122)
- La consumer key des secrets Cursor avait des règles enregistrées avec une **tabulation
  en tête de chemin** (`"\t/cloud/project/…"`) → « This call has not been granted » sur
  tous les appels. La recréation manuelle par l'utilisateur (`artcb-deploy-api`) a reproduit
  la même corruption (tabulation insérée par le copier-coller navigateur).
- L'ancienne clé à droits complets était **codée en dur dans le dépôt public**
  (`scripts/check_ovh.py`, historique git) : exposition critique.

### Solution appliquée
La demande de credential a été créée **par l'API** (`POST /auth/credential`) avec des règles
construites programmatiquement (aucune tabulation possible), scopées au strict nécessaire :

```text
GET     /cloud/project
GET     /cloud/project/<project_id>
GET     /cloud/project/<project_id>/*
POST    /cloud/project/<project_id>/*
PUT     /cloud/project/<project_id>/*
DELETE  /cloud/project/<project_id>/*
```

L'utilisateur n'a eu qu'à **cliquer l'URL de validation SSO OVH** (aucun chemin à saisir).

### Credentials révoquées (vérifié par appel API post-révocation)
| ID | Description | Motif |
|---|---|---|
| `629869000` | MDBAI-Production-1, droits complets, sans expiration, **CK dans le git public** | Exposée — révoquée, testée morte (« This credential does not exist ») |
| `632781111` | cursor-artcb-ovh-agent | Règles corrompues (tabulation) |
| `632793553` | artcb-deploy-api (recréation manuelle) | Règles corrompues (tabulation) |

### Credentials restantes sur le compte (pour revue utilisateur)
`629815737`, `629870423`, `629882353`, `629925024`, `629946059` (validées, sans expiration,
apps « AS »/« MDBAI ») — potentiellement utilisées par d'autres systèmes de l'utilisateur,
non révoquées par prudence. `631847905/631849587/631852152` expirent d'elles-mêmes le
2026-08-30. Les credentials `629815299/629815407/629815712/629880291/629882086` sont expirées.

### Nouvelle clé active
- Consumer key : `c940e818…` (validée « Unlimited », règles propres — vérifié
  `/auth/currentCredential`).
- Testée : liste du projet, liste des instances (`artcb-node-1 ACTIVE 152.228.144.34`). ✅

## 3. Bascule Doppler — zéro secret sur le serveur

- Token service Doppler (`artcb-blockchain/dev`, lecture seule) posé dans
  `/etc/artcb/doppler.env` — root-only `600`, référencé par l'unité systemd
  (`EnvironmentFile=-`), consommé par `scripts/start_node.sh` → `doppler run --`.
- `.env` **détruit** (`shred -u`) ; wallet réinitialisé et chiffré avec la
  `ARTCB_WALLET_PASSPHRASE` de Doppler.
- Preuve d'injection : `/health` → `bob_configured: true` (BOB_API_KEY n'existe que
  dans Doppler).
- Doppler CLI v3.76.5 installé sur le serveur et la VM agent.

## 4. Tests finaux (mode Doppler, conditions de production)

```text
519 passed, 8 skipped in 434.38s (0:07:14)
```

- Exécutés sur l'instance avec `doppler run -- pytest tests/ -q` (mêmes secrets que le service).
- 8 skipped = bridges live (nécessitent des services externes payants — comportement attendu,
  cf. HANDOFF).
- Santé vérifiée **depuis l'extérieur** après tests : `status: ok`, PQC actif.

## 5. Actions restantes (utilisateur, hors périmètre agent)

1. **Doppler** (`artcb-blockchain/dev`) : `OVH_CONSUMER_KEY` → `c940e818…` (valeur complète
   fournie dans le chat), `ARTCB_PORT` 5000 → 8000, ajouter `OVH_SSH_PRIVATE_KEY` (bloc fourni
   dans le chat), supprimer `OVH_CONSUMER_KEY_EXPIRED` / `OVH_CONSUMER_KEY_NEW` /
   `OVH_VALIDATION_URL_NEW`.
2. **Secrets Cursor** (Cloud Agents → Secrets) : mettre à jour `OVH_CONSUMER_KEY`,
   ajouter `DOPPLER_TOKEN` (les futurs agents auront alors API OVH + SSH + toute la config).
3. **GitHub Actions** : seul `ARTCB_WALLET_PASSPHRASE` est utilisé (`tests.yml`),
   indépendant du serveur — rien à faire sauf échec CI.
4. Revue des credentials OVH restantes (§2) si elles ne servent plus.

## 6. Accès au serveur

- SSH : `ubuntu@152.228.144.34` — clés autorisées : `artcb-deploy` (utilisateur) et
  `artcb-cloud-agent-20260819` (agent ; la clé privée doit être ajoutée dans Doppler
  sous `OVH_SSH_PRIVATE_KEY` pour les futurs agents).
- API : `http://152.228.144.34:8000` (HTTP direct — TLS/reverse-proxy = prochaine étape
  possible : nginx + certbot ou IP failover + domaine).
