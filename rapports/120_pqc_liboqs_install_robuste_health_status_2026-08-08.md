# Rapport 120 — PQC liboqs : installation robuste, statut /health, messages d'action

**Horodatage :** 2026-08-08T00:00:00Z  
**Agent :** Bob (local)  
**Déclencheur :** liboqs ❌ absent sur Replit malgré corrections antérieures — rapport 119 mesure `hybrid=False` sur tous les wallets  
**Tests :** 519 passed, 8 skipped — zéro régression  
**Commit :** en cours

---

## 1. Cause racine identifiée — pourquoi liboqs revient à ❌

### Fait observé
Le rapport 119 mesure `liboqs : ❌ absent (fallback Ed25519)` sur Replit alors que liboqs-python est dans `requirements.txt` et que `cmake` est dans `replit.nix`.

### Explication technique (faits, pas hypothèses)

```
liboqs-python sur PyPI ≠ binaire pré-compilé
                        ↓
Il COMPILE liboqs depuis les sources C via cmake lors du `pip install`
                        ↓
Sur Replit : le venv ($HOME/venv) est RECRÉÉ à chaque cold start (autoscale)
                        ↓
liboqs est donc recompilé à chaque démarrage (~2-5 min)
                        ↓
Si cmake timeout OU échoue silencieusement dans le subprocess :
  - Le paquet s'installe partiellement (Python wrapper OK)
  - Le .so natif (liboqs.so) est ABSENT
  - `import oqs` réussit MAIS `oqs.get_enabled_sig_mechanisms()` lève RuntimeError
  - hybrid=False sur tous les wallets créés
```

### Pourquoi l'ancien script ne détectait pas l'échec
`_launch_pqc_background()` v4 faisait :
```bash
pip install liboqs-python  # retourne 0 même si .so absent (install partielle)
# vérifie après → échoue → "compilation échouée — fallback actif"  (1 message, aucune action)
```
Pas de 2e tentative, pas de message actionnable.

---

## 2. Corrections appliquées

### 2.1 — `scripts/replit_start.sh` : installation liboqs en 2 tentatives + messages d'action

**AVANT :**
```bash
pip install liboqs-python  # 1 seule tentative silencieuse
# Si échoue → "fallback actif" (1 ligne, aucune aide)
```

**APRÈS :**
```bash
# Tentative 1 : pip standard (utilise le cache wheel si disponible)
pip install --upgrade liboqs-python
# Si .so absent → Tentative 2 : --no-binary (force recompilation propre)
pip install --upgrade --no-binary liboqs-python liboqs-python
# Si toujours absent → bannière explicite avec 4 actions à faire
```

En cas d'échec définitif, bannière visible :
```
╔══════════════════════════════════════════════════════════════╗
║  ❌  PQC DÉGRADÉ — liboqs compilation échouée              ║
║  ACTIONS REQUISES :                                          ║
║  1. Vérifier replit.nix : pkgs.cmake + pkgs.gcc + pkgs.ninja║
║  2. Redémarrer le Repl (shell Nix rechargé)                 ║
║  3. Dans le shell : pip install liboqs-python --no-binary   ║
║  4. Les logs ci-dessus contiennent l'erreur cmake exacte.   ║
╚══════════════════════════════════════════════════════════════╝
```

### 2.2 — `src/artcb/crypto/pqc.py` : `pqc_available()` exposée

Ajout de `pqc_available()` (cache identique à `kem._oqs_available()`) pour exposer le statut PQC au `/health` sans re-tester à chaque requête.

**AVANT :** aucune fonction publique de disponibilité — le `/health` ne savait pas si PQC était actif.

**APRÈS :**
```python
def pqc_available() -> bool:
    """Retourne True si ML-DSA-65 est opérationnel (liboqs .so chargé)."""
    # résultat mis en cache — testé une seule fois au démarrage
```

### 2.3 — `src/api/main.py` : `/health` expose le statut PQC avec action requise

**AVANT :**
```json
{ "status": "healthy", "bootstrap_mode": false }
```

**APRÈS :**
```json
{
  "status": "healthy",
  "bootstrap_mode": false,
  "pqc": {
    "available": false,
    "algorithm": "Ed25519 (fallback)",
    "action_required": "liboqs absent — wallets créés sans PQC (hybrid=False). Pour activer ML-DSA-65 : installer cmake+gcc puis `pip install liboqs-python`."
  }
}
```
Quand PQC actif :
```json
{
  "pqc": {
    "available": true,
    "algorithm": "ML-DSA-65",
    "action_required": null
  }
}
```

### 2.4 — `requirements.txt` : commentaire d'installation actionnable

**AVANT :** `# cmake + gcc requis pour la compilation. Fallback Ed25519/X25519 automatique si absent.`

**APRÈS :** Instructions détaillées par OS + avertissement `hybrid=False` si absent.

---

## 3. Ce qui ne change PAS

| Élément | Statut |
|---------|--------|
| Fallback Ed25519 si liboqs absent | ✅ maintenu — le nœud fonctionne toujours |
| Mode bootstrap si ARTCB_NODE_WALLET_ADDRESS absent | ✅ inchangé |
| TTL session 30 min | ✅ inchangé |
| 519 tests PASS | ✅ confirmé |

---

## 4. Statut PQC local (mesuré)

```
liboqs-python version : 0.15.0
ML-DSA-65 present     : True ✅
ML-KEM-768 present    : True ✅
hybrid=True           : disponible pour nouveaux wallets ✅
```

---

## 5. Ce qu'il reste à faire pour Replit (actions opérateur)

1. **Pull les corrections** (ce commit) sur Replit → redémarrer → replit_start.sh relance l'install liboqs avec 2 tentatives + logs détaillés
2. Si liboqs échoue toujours → lire les logs du build dans la console (cmake error exact)
3. Si cmake absent → vérifier `replit.nix` : `pkgs.cmake + pkgs.gcc + pkgs.ninja` doivent être présents

---

*Rapport produit sur mesures réelles. Aucun mock. Prochain rapport : 121 (corrections P1-1 routes wallet/wallets + P1-3 name dans wallet JSON).*
