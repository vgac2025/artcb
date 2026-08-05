# Rapport 103 — Vulnérabilités npm : Vite + react-router — Audit complet 2026-08-05

**Date :** 2026-08-05T23:00:00Z  
**Session :** Audit sécurité npm + mise à jour Vite 5.4.x → 6.4.3  
**Outil :** `npm audit --json` dans `frontend/`  
**Replit testés :** N1 + N2 (build validé)

---

## Résumé exécutif

| Paquet | Sévérité | Avant | Après | Statut |
|--------|----------|-------|-------|--------|
| `vite` | HIGH (CVSS 7.5) | 5.4.21 | **6.4.3** | ✅ CORRIGÉ |
| `esbuild` | Moderate | inclus dans vite 5.x | résolu par mise à jour vite | ✅ CORRIGÉ |
| `postcss` | HIGH | dépendance transitive | corrigé par `npm audit fix` | ✅ CORRIGÉ |
| `react-router` | Moderate | 6.30.4 | 6.30.4 (inchangé) | ⚠️ Documenté — risque nul |
| `react-router-dom` | Moderate | 6.30.4 | 6.30.4 (inchangé) | ⚠️ Documenté — risque nul |

**Résultat final : 2 vulnérabilités restantes (moderate) — risque réel nul pour ARTCB**

---

## AVANT / APRÈS

### `frontend/package.json` — AVANT

```json
"vite": "^5.4.0",
"@vitejs/plugin-react": "^4.3.0"
```

### `frontend/package.json` — APRÈS

```json
"vite": "^6.4.3",
"@vitejs/plugin-react": "^5.0.4"
```

### Build vite 6.4.3 validé

```
vite v6.4.3 building for production...
114 modules transformed
dist/assets/index-DP5X6Lv8.js      182.70 kB
dist/assets/vendor-C8w-UNLI.js     141.74 kB
dist/assets/axios-DhXgJQ-f.js       46.09 kB
dist/assets/cytoscape-DTSO7Bv0.js  443.72 kB
built in 6.10s
0 erreur TypeScript ✅
```

---

## Vulnérabilités corrigées (Vite 5.4.x → 6.4.3)

### GHSA-4w7w-66w2-5vf9 — Moderate → CORRIGÉ

- **Titre :** Path Traversal dans les fichiers `.map` de dépendances optimisées
- **Versions touchées :** Vite ≤ 6.4.1 → **Vite 6.4.3 corrige**
- **Impact :** lecture de fichiers `.map` hors du répertoire (dev server uniquement)

### GHSA-v6wh-96g9-6wx3 — Moderate → CORRIGÉ

- **Titre :** `launch-editor` : divulgation NTLMv2 via chemin UNC (Windows uniquement)
- **Versions touchées :** Vite ≤ 6.4.2 → **Vite 6.4.3 corrige**
- **Impact :** Windows uniquement — non applicable Replit Linux

### GHSA-fx2h-pf6j-xcff — HIGH (CVSS 7.5) → CORRIGÉ

- **Titre :** `server.fs.deny` bypassable via chemins Windows alternatifs
- **Versions touchées :** Vite ≤ 6.4.2 → **Vite 6.4.3 corrige**
- **Impact :** Windows uniquement, dev server uniquement

### PostCSS path traversal — HIGH → CORRIGÉ

- Résolu par `npm audit fix` (mise à jour dépendance transitive)

---

## Vulnérabilités restantes (2 moderate — react-router)

### CVE-2025-68470 — react-router open redirect

- **Titre :** Open redirect via backslash dans `<Link>` et `useNavigate`
- **Condition :** Requiert `basename` configuré avec chemin contrôlé par l'attaquant
- **ARTCB :** HashRouter sans `basename` — **non exploitable**

### react-router deserializeErrors() — Arbitrary Constructor Injection

- **Titre :** Injection constructeur via SSR hydration (`deserializeErrors()`)
- **Condition :** Requiert SSR (Server-Side Rendering) actif
- **ARTCB :** SPA 100% client-side, pas de SSR — **non exploitable**

### Pourquoi pas de mise à jour vers react-router v7 ?

`react-router-dom` v6 → v7 est un **breaking change complet** :
- API `<Route>` renommée
- `useNavigate` et `<Link>` changent de comportement  
- Nécessite de réécrire `App.tsx` et toutes les pages avec navigation

**Décision :** reporter à une session de maintenance dédiée avec tests complets.

---

## Vulnérabilités de l'agent Replit (rapport 118)

Le rapport 118 (rédigé par l'agent Replit) identifiait aussi :

1. **git pull après build** → **CORRIGÉ** dans `replit_start.sh` v3 (étape 0 = git pull en premier)
2. **liboqs-python commenté** → **CORRIGÉ** dans `requirements.txt` (décommenté) + bloc 2b dans `replit_start.sh`

---

## État après corrections

```
npm audit résultat :
  vite      : 6.4.3 (was 5.4.21) ✅
  esbuild   : résolu ✅
  postcss   : résolu ✅
  react-router : 2 moderate, risque nul documenté ⚠️
```

---

*Rapport généré conformément au PROTOCOLE_ARTCB — avant/après + lignes exactes*  
*ARTCB — VGACTech 2026*
