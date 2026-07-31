# Rapport 094 — SSH persistant Replit + MCP Bob + API Reference + docs
**Date :** 2026-08-01  
**Statut :** ✅ 371/371 PASS  
**Phase :** 12.1 + 12.5.6 + infrastructure Replit SSH

---

## 1. SSH persistant Replit (`scripts/setup_ssh_git.sh`)

### Problème résolu
À chaque changement de compte Replit ou redémarrage de session, la clé SSH était régénérée → GitHub ne reconnaissait plus la clé → `git push` échouait.

### Solution
[`scripts/setup_ssh_git.sh`](scripts/setup_ssh_git.sh) — script à exécuter manuellement une fois par session :

```
Ordre de recherche de la clé SSH :
  1. Variable SSH_PRIVATE_KEY (secret Replit ou env)
  2. doppler secrets get SSH_PRIVATE_KEY → clé récupérée depuis Doppler
  3. Variable SSH_REPLIT (clé publique seule — push impossible)
  4. Génération d'urgence (affiche la nouvelle clé à ajouter sur GitHub)
```

**La clé ne change jamais** — elle est stockée dans Doppler et récupérée à chaque session.

### Stockage dans Doppler
La clé privée ARTCB (`vgac42@gmail.com`) est maintenant dans Doppler :
```
Projet : artcb-blockchain
Config : dev
Secret : SSH_PRIVATE_KEY
```

### Intégration automatique
[`scripts/replit_start.sh`](scripts/replit_start.sh) appelle `setup_ssh_git.sh` avant le démarrage de l'API. À chaque `bash scripts/replit_start.sh`, la clé SSH est restaurée.

### Usage Replit (changement de compte)
```bash
# Étape unique — à faire une fois par nouvelle session :
bash scripts/setup_ssh_git.sh

# Vérification
ssh -T git@github.com      # Hi vgac2025!
git push origin main       # fonctionne
```

---

## 2. Phase 12.1.10 ✅ Config Bob IDE

[`.bob/mcp.json`](.bob/mcp.json) créé :
```json
{
  "mcpServers": {
    "artcb-blockchain": {
      "command": "python",
      "args": ["-m", "src.artcb.mcp.server"],
      "env": {"ARTCB_API_URL": "http://localhost:8000"}
    }
  }
}
```
Bob peut maintenant utiliser directement les 5 tools ARTCB (`artcb_memo`, `artcb_think`, `artcb_search`, `artcb_mine`, `artcb_store`).

---

## 3. Phase 12.1.15 ✅ Documentation MCP

[`docs/MCP_SETUP.md`](docs/MCP_SETUP.md) créé :
- Instructions pour Bob, Cursor, VSCode, Claude Desktop, Replit Agent
- Tableau des 5 tools avec paramètres
- Tableau des 2 resources

---

## 4. Phase 12.5.6 ✅ API Reference mise à jour

[`docs/API_REFERENCE_ARTCB.md`](docs/API_REFERENCE_ARTCB.md) créé :
- Documentation complète de tous les endpoints
- **`graph_id` clairement marqué optionnel** dans `/store` (si `text` fourni)
- Nouveau champ `hybrid` + `address_v2` dans `wallet/create`
- Notes anti-Sybil, cache encode, signatures hybrides

---

## État Phase 12 après cette session

| Jalon | Statut |
|-------|--------|
| 12.1.10 Config Bob IDE | ✅ |
| 12.1.15 docs MCP_SETUP.md | ✅ |
| 12.5.1 /store async | ✅ |
| 12.5.2 auto-encode dans /store | ✅ |
| 12.5.3 wallet hybrid+address_v2 | ✅ |
| 12.5.5 cache IR | ✅ |
| 12.5.6 API_REFERENCE_ARTCB | ✅ |
| 12.3.2 .replit + replit.nix | ✅ |
| 12.3.3 .devcontainer | ✅ |
| 12.3.4 Dockerfile | ✅ |
| 12.3.5 docker-compose.yml | ✅ |

**Tests : 371/371 PASS — commit `b4c2e18` → `main`**

---

## Prochains jalons P1

| Phase | Jalon |
|-------|-------|
| 12.1.1–12.1.9 | Vérifier les tests MCP (24/24 PASS ✅ — déjà fait) |
| 12.3.1 | `flake.nix` environnement Nix reproductible |
| 12.3.6 | `render.yaml` / `railway.toml` deploy 1-clic |
| 13 | Déploiement OVH (Terraform / image custom) |

---

*ARTCB v0.3.0 — 2026-08-01*
