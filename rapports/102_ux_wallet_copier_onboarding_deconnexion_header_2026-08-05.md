# Rapport 102 — Bugs UX wallet : copier, onboarding, déconnexion, wallet actif header
**Date :** 2026-08-05T22:00:00Z  
**Session :** UX wallet — correction 4 bugs signalés par l'utilisateur  
**Replit testés :** N1 `https://lvx--supermicro20238.replit.app` + N2 `https://lvx--supermicro20239.replit.app`

---

## Bugs identifiés et corrigés

### UX-1 — Pas de bouton Copier sur les wallets existants dans la grille

**AVANT :** Cliquer sur un wallet dans la grille ouvrait uniquement l'historique des rewards.  
Aucun bouton pour copier l'adresse directement depuis la grille des wallets.  
L'utilisateur devait créer un nouveau wallet pour voir le bouton Copier.

**APRÈS (`frontend/src/pages/Wallets.tsx`) :**
- Bouton copier `⧉` sur chaque wallet dans la grille (icône copie)
- Indicateur visuel `✓` après copie réussie (2 secondes)
- Bouton `▶ Activer` pour changer de wallet actif directement depuis la grille
- Fonctions ajoutées : `copyFromGrid(addr)` + state `copiedGrid`
- Fallback `document.execCommand("copy")` si Clipboard API indisponible

---

### UX-2 — Aucun message pour un utilisateur sans wallet (onboarding)

**AVANT :**
- Grille vide sans aucune explication
- Un nouvel utilisateur arrivant sur le dashboard ne savait pas quoi faire
- `Home.tsx` : aucun CTA visible si `walletCount === 0`

**APRÈS :**

**`Home.tsx`** — Bandeau d'accueil doré si `walletCount === 0` et aucun wallet actif :
```
◇ Bienvenue sur ARTCB — Commencez par créer votre wallet !
Un wallet est votre identité sur la blockchain. [Créer mon wallet →]
```

**`Wallets.tsx`** — Grille vide avec message explicatif :
```
◇
Vous n'avez pas encore de wallet.
Un wallet est votre identité sur la blockchain ARTCB — il vous permet de signer des blocs
et de recevoir des récompenses ARTCB.
```
Titre de la grille : `Vos wallets (0) — Créez votre premier wallet ci-dessus ↑`

---

### UX-3 — Bouton déconnexion absent

**AVANT :** Une fois `actorAddress` défini, impossible de le vider.  
Aucun bouton "Se déconnecter" nulle part dans l'interface.  
L'utilisateur restait "connecté" avec l'ancien wallet même s'il voulait en changer.

**APRÈS :**

**`Wallets.tsx`** — Panneau wallet actif en haut de page avec bouton `✕ Se déconnecter` :
```
◇ Wallet actif : artcb1xxxx…  [Copier] [✕ Se déconnecter]
```

**`DashboardLayout.tsx` (header)** — Bouton déconnexion visible sur **toutes** les pages :
```
◇ artcb1xxxx…  [✕]
```
- La déconnexion vide uniquement `actorAddress` en mémoire — les wallets restent sur le serveur
- Fonction : `handleDisconnect()` → `setActorAddress("")`

---

### UX-4 — Wallet actif non visible dans le header global

**AVANT :** Aucun indicateur dans le header global du wallet actuellement actif.  
L'utilisateur ne savait pas quel wallet était "actif" sur n'importe quelle page.

**APRÈS (`frontend/src/layout/DashboardLayout.tsx`) :**

Si wallet actif :
```
◇ artcb1xxxxxxxx…  [✕]    ← vert, cliquable → /wallets, bouton rouge déconnexion
```
Si aucun wallet actif :
```
◇ Wallet ?    ← doré, cliquable → /wallets
```

---

## AVANT / APRÈS code

### `Wallets.tsx` — grille avant
```tsx
<div className="mc-chest-icon">◇</div>
<div className="mc-chest-name">{w.name}</div>
<div className="mc-gold-text">{balance} ₳</div>
<div className="mc-mono mc-chest-addr">{addr.slice(0,8)}…</div>
```

### `Wallets.tsx` — grille après
```tsx
{w.address === actorAddress && <div style="font-size:8px; color:green">● ACTIF</div>}
<div className="mc-chest-icon">◇</div>
<div className="mc-chest-name">{w.name}</div>
<div className="mc-gold-text">{balance} ₳</div>
<div className="mc-mono mc-chest-addr">{addr.slice(0,8)}…</div>
<div>
  <button onClick={() => copyFromGrid(w.address)}>⧉ / ✓</button>
  <button onClick={() => setActorAddress(w.address)}>▶</button>
</div>
```

### `DashboardLayout.tsx` — header avant
```tsx
{/* Aucun indicateur wallet */}
```

### `DashboardLayout.tsx` — header après
```tsx
{actorAddress ? (
  <span>
    <Link to="/wallets">◇ {actorAddress.slice(0,12)}…</Link>
    <button onClick={() => setActorAddress("")}>✕</button>
  </span>
) : (
  <Link to="/wallets">◇ Wallet ?</Link>
)}
```

### `index.css` ajouté
```css
.mc-chest-active {
  border-color: var(--mc-grass, #56c426) !important;
  background: rgba(86, 196, 38, 0.08) !important;
}
```

---

## Tests réels N1+N2 (2026-08-05)

| Test | N1 | N2 |
|------|----|----|
| GET /health | ✅ 200 ok | ✅ 200 ok |
| GET /wallet/list | ✅ 0 wallets (éphémère) | ✅ 2 wallets |
| POST /wallet/create | ✅ adresse créée | ✅ adresse créée |
| GET /wallet/balance/{addr} | ✅ 0.0 ARTCB | ✅ 0.0 ARTCB |
| GET /chain | ✅ 0 blocs | ✅ 0 blocs |

**Total : 10/10 PASS**

### Observation API Replit
- `POST /wallet/create` retourne `{name, address, public_key_hex, public_key_b64, hybrid}`
- `hybrid: false` sur Replit car liboqs non installé → Ed25519 standard (normal)
- `address_v2` absent → code frontend le gère en optionnel (`address_v2?`) ✅

---

## Build frontend
```
tsc -b && vite build : 0 erreur TypeScript
117 modules transformés / built in 6.14s
```

---

## Résumé corrections

| Bug | Fichier | Statut |
|-----|---------|--------|
| UX-1 Copier adresse depuis la grille | Wallets.tsx | ✅ CORRIGÉ |
| UX-2 Onboarding premier utilisateur | Home.tsx + Wallets.tsx | ✅ CORRIGÉ |
| UX-3 Bouton déconnexion | Wallets.tsx + DashboardLayout.tsx | ✅ CORRIGÉ |
| UX-4 Wallet actif dans header | DashboardLayout.tsx | ✅ CORRIGÉ |
| CSS wallet actif | index.css | ✅ CORRIGÉ |

---

*Rapport généré conformément au PROTOCOLE_ARTCB — avant/après + lignes exactes*  
*ARTCB — VGACTech 2026*
