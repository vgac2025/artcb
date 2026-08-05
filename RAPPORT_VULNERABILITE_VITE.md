# Rapport de vulnérabilité — `vite` (frontend)

> **Statut : Non résolu — aucune modification effectuée**
> Date du rapport : août 2026

---

## 1. Contexte

Le frontend ARTCB utilise **Vite 5.4.x** comme bundler/serveur de développement.  
L'outil `npm audit` signale **3 vulnérabilités** sur ce paquet, dont une classée **High**.

---

## 2. Les 3 vulnérabilités détectées

### 🟠 CVE / GHSA-4w7w-66w2-5vf9 — Sévérité : Moderate

| Champ | Détail |
|---|---|
| **Titre** | Path Traversal dans la gestion des fichiers `.map` de dépendances optimisées |
| **Type** | CWE-22 (Path Traversal) + CWE-200 (Information Exposure) |
| **Versions touchées** | Vite ≤ 6.4.1 |
| **Impact** | Un attaquant peut demander un fichier `.map` spécialement forgé pour lire des fichiers en dehors du répertoire prévu |

### 🟠 GHSA-v6wh-96g9-6wx3 — Sévérité : Moderate

| Champ | Détail |
|---|---|
| **Titre** | `launch-editor` : divulgation de hash NTLMv2 via chemin UNC sur Windows |
| **Type** | CWE-73 (External Control of File Name) + CWE-522 (Credentials insuffisamment protégées) |
| **Versions touchées** | Vite ≤ 6.4.2 |
| **Impact** | Sur Windows uniquement, l'ouverture de l'éditeur depuis le navigateur peut exposer le hash d'authentification réseau NTLMv2 de l'utilisateur |

### 🔴 GHSA-fx2h-pf6j-xcff — Sévérité : **High** — CVSS 7.5

| Champ | Détail |
|---|---|
| **Titre** | `server.fs.deny` contournable via chemins alternatifs Windows |
| **Type** | CWE-22 (Path Traversal) + CWE-200 (Information Exposure) |
| **Versions touchées** | Vite ≤ 6.4.2 |
| **Score CVSS** | **7.5 / 10** (réseau, sans authentification, sans interaction utilisateur) |
| **Impact** | La directive `server.fs.deny` (qui empêche Vite de servir certains fichiers sensibles) peut être contournée sur Windows via des chemins alternatifs (ex. `/C:/Windows/...` au lieu de `C:\Windows\...`) |

---

## 3. Pourquoi c'est signalé « Unresolved »

`npm audit fix` ne peut pas corriger automatiquement ces vulnérabilités car le saut de version correctif (**Vite 8.2.0**) est un **changement majeur** (de v5 à v8). NPM refuse d'appliquer ce type de mise à jour sans intervention humaine explicite.

---

## 4. Évaluation du risque réel pour ARTCB sur Replit

| Critère | Situation actuelle |
|---|---|
| Environnement d'exécution | Replit (Linux) — **pas Windows** |
| Vite exposé publiquement ? | **Non** — le serveur `vite dev` n'est pas utilisé en production. La commande `npm run build` génère des fichiers statiques servis par FastAPI. |
| Qui peut accéder au dev server ? | Uniquement lors du développement local sur la machine du développeur |
| Vulnérabilités Windows applicables ici ? | **Non** (NTLMv2, chemins UNC, chemins alternatifs Windows) |

> **Conclusion : le risque en production est nul.** Les vulnérabilités affectent le serveur de développement Vite (`vite dev`), qui n'est jamais lancé en production — ARTCB Replit compile le frontend en fichiers statiques puis les sert via FastAPI.

---

## 5. Solution envisageable

### Option A — Mise à jour majeure vers Vite 8.x *(résout tout)*

```bash
cd frontend
npm install vite@^8.2.0 @vitejs/plugin-react@^4 --save-dev
npm run build   # vérifier que le build passe toujours
```

**Points de vigilance avant de faire cette mise à jour :**
- Vite 8 requiert **Node.js 20+** (vérifier : `node --version`)
- Le fichier `vite.config.ts` peut nécessiter des ajustements d'API
- Les imports de plugins doivent être revérifiés

### Option B — Ignorer (acceptable dans ce cas précis)

Documenter explicitement dans `package.json` ou `.npmrc` que ces alertes sont connues et non exploitables dans ce contexte de déploiement (build statique, Linux, pas de `vite dev` en prod).

---

## 6. Recommandation

| Priorité | Action |
|---|---|
| **Court terme** | Ne rien faire — le risque réel est nul dans l'architecture actuelle |
| **Moyen terme** | Planifier la mise à jour vers Vite 8.x lors d'une session de maintenance dédiée, en testant le build complet après migration |

---

*Rapport généré à partir de `npm audit --json` dans `frontend/` — aucun fichier modifié.*
