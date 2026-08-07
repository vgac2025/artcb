# Roadmap ARTCB — État complet 2026-08-07
**Mise à jour : rapport 114**  
**Suite tests : 519 PASS, 8 skipped**  
**Commit : à pousser — rapport 114**

---

## LÉGENDE

```
✅ Implémenté et testé
🟡 Partiellement implémenté
❌ Non implémenté — dans roadmap
📋 Identifié — à planifier
```

---

## PHASE 1 — Infrastructure de base (✅ complète)

| ID | Fonctionnalité | Status |
|----|---------------|--------|
| P1-1 | IR Engine (encodage/décodage graphes) | ✅ |
| P1-2 | Blockchain PoL (Proof-of-Learning) | ✅ |
| P1-3 | Wallets Ed25519 + ML-DSA-65 (PQC) | ✅ |
| P1-4 | Chiffrement AES-256-GCM wallets | ✅ |
| P1-5 | Dual-agent (Explorer + Critic) | ✅ |
| P1-6 | PoL scorer (alpha/beta/gamma) | ✅ |
| P1-7 | Chain manager (JSONL append) | ✅ |
| P1-8 | Vector store + semantic search | ✅ |
| P1-9 | API REST FastAPI complète (100+ endpoints) | ✅ |
| P1-10 | Frontend React (dashboard MC) | ✅ |

---

## PHASE 2 — Sécurité et authentification (✅ complète depuis rapport 107)

| ID | Fonctionnalité | Rapport | Status |
|----|---------------|---------|--------|
| P2-1 | `POST /wallet/create` — password obligatoire | 107 | ✅ |
| P2-2 | `seed_hex` retournée UNE SEULE FOIS | 107 | ✅ |
| P2-3 | `POST /auth/login` (nom + mot de passe → session) | 107 | ✅ |
| P2-4 | `GET /auth/challenge` + `POST /auth/verify` (signature Ed25519) | 107 | ✅ |
| P2-5 | `POST /auth/logout` (invalidation session) | 107 | ✅ |
| P2-6 | `POST /api-keys/generate` — session obligatoire | 107 | ✅ |
| P2-7 | Anti-Sybil pré-filtrage (wallets en cooldown exclus) | 109 | ✅ |
| P2-8 | Identité matérielle (device fingerprint TPM + machine-id) | 114 | ✅ |
| P2-9 | Anti-fraude 1 wallet/appareil (wallet_device_binding) | 114 | ✅ |
| P2-10 | `GET /wallet/list` protégé (à implémenter) | 113 | ❌ |
| P2-11 | Rate limiting sur `/auth/login` | 113 | ❌ |
| P2-12 | CORS restreint en production | 113 | ❌ |
| P2-13 | Migration anciens wallets vers user_password | 113 | ❌ |

---

## PHASE 3 — P2P réseau (🟡 partiel)

| ID | Fonctionnalité | Rapport | Status |
|----|---------------|---------|--------|
| P3-1 | Node identity (ML-KEM keypair) | 065 | ✅ |
| P3-2 | PeerManager (registre pairs) | 065 | ✅ |
| P3-3 | P2P sync blocs publics chiffrés | 065 | ✅ |
| P3-4 | Pool distribué E2E ML-KEM | 065 | ✅ |
| P3-5 | `POST /p2p/register-public` (auto-enregistrement) | 114 | ✅ |
| P3-6 | Bootstrap nodes fixés (N1/N2) | — | ❌ À implémenter |
| P3-7 | Auto-découverte au démarrage (contact bootstrap) | — | ❌ À implémenter |
| P3-8 | Gossip protocol (échange listes de pairs) | — | 🟡 Code présent |
| P3-9 | DHT Kademlia (libp2p) | 096 | 🟡 Code présent |
| P3-10 | mDNS local (LAN) | — | ❌ Roadmap |
| P3-11 | `ARTCB_NODE_PUBLIC_URL` configuré au démarrage | — | ❌ À ajouter dans `.env` |

---

## PHASE 4 — Intégrations et connecteurs (✅ complète)

| ID | Fonctionnalité | Status |
|----|---------------|--------|
| P4-1 | ChatGPT / OpenAI connector | ✅ |
| P4-2 | Claude / Anthropic connector | ✅ |
| P4-3 | IBM Bob connector | ✅ |
| P4-4 | API keys Bearer `artcb_xxx` | ✅ |
| P4-5 | Webhooks sortants | ✅ |
| P4-6 | SDK Python | ✅ |

---

## PHASE 5 — Infrastructure CI/CD (✅ complète depuis rapport 114)

| ID | Fonctionnalité | Rapport | Status |
|----|---------------|---------|--------|
| P5-1 | GitHub Actions CI — 519 tests automatisés | 114 | ✅ |
| P5-2 | GitHub Secrets (remplace Doppler) | 114 | ✅ |
| P5-3 | `register-node.yml` — enregistrement auto nœud | 114 | ✅ |
| P5-4 | Replit N1/N2 déploiement automatique | 100 | ✅ |
| P5-5 | LoopQA tests qualité automatisés | 101-110 | ✅ |

---

## PHASE 6 — Identité matérielle avancée (🟡 en cours — roadmap TPM)

| ID | Fonctionnalité | Rapport | Status |
|----|---------------|---------|--------|
| P6-1 | Device fingerprint multi-niveau (machine-id + TPM) | 114 | ✅ |
| P6-2 | Wallet device binding (1 wallet/machine) | 114 | ✅ |
| P6-3 | TPM EK Certificate lecture (tpm2-tools) | 114 | ✅ code, 🟡 accès groupe `tss` |
| P6-4 | TPM Attestation Key (AK) LVX | — | ❌ Prochaine étape |
| P6-5 | LVX Hardware Identity Certificate format | — | ❌ À définir |
| P6-6 | Vérification AK sur le réseau (preuve machine physique) | — | ❌ Roadmap |
| P6-7 | Android ICCID + IMEI fingerprint | — | ❌ Roadmap mobile |
| P6-8 | iOS DeviceCheck API | — | ❌ Roadmap mobile |
| P6-9 | 1 wallet/SIM (mobile anti-fraude) | — | ❌ Roadmap mobile |

---

## PHASE 7 — Sous-domaines et DNS nœuds (📋 à planifier)

| ID | Fonctionnalité | Status |
|----|---------------|--------|
| P7-1 | Bootstrap nodes configurés (`.env ARTCB_BOOTSTRAP_NODES`) | ❌ |
| P7-2 | Sous-domaines automatiques `node-XXXX.artcb.network` | ❌ Serveur DNS requis |
| P7-3 | Standard `ARTCB_NODE_PUBLIC_URL` dans `.env` | ❌ À ajouter |
| P7-4 | Domaine custom pour utilisateurs Replit Premium | 113 | 📋 Documentation |
| P7-5 | Annuaire public des nœuds actifs | ❌ |

---

## PHASE 8 — Tokenomics et halving (✅ complète)

| ID | Fonctionnalité | Status |
|----|---------------|--------|
| P8-1 | Halving dynamique | ✅ |
| P8-2 | Récompenses PoL proportionnelles | ✅ |
| P8-3 | Faucet devnet | ✅ |
| P8-4 | Balance tracking on-chain | ✅ |

---

## PHASE 9 — Ce qui a été fait DEPUIS la roadmap 073 (juillet 2026)

> Tous ces éléments n'étaient pas dans la roadmap 073 — ils ont été implémentés entre rapports 074 et 114.

| Rapport | Description |
|---------|-------------|
| 074 | Corrections P0/P1 backend |
| 075-076 | Anti-Sybil, bypass IA, calibrage métriques |
| 077 | Ingestion KB i18n, 234→502 tests |
| 079-081 | Étude économique, halving dynamique, PoL universel |
| 082 | IR v0.2, NFT transfer, PoL phase 11 |
| 083 | Résolution complète P0/P1 |
| 084-086 | SDK Python, relay QA live, MCP interop |
| 087-090 | PQC natif, ngrok décentralisation, PDF threadsafe |
| 091-094 | OVH audit, async store mining, deploy universel, SSH persistant |
| 095-098 | libp2p natif Kademlia, gossipsub, 409 tests catalogue |
| 099 | Audit smoke hardcoding/placeholder/stub |
| 100-104 | Replit setup, LoopQA, UX wallet, vulnérabilités npm |
| 105-106 | Investigation N1/N2, audit sécurité faille actor_address |
| **107** | **Auth complète : login, challenge, verify, logout, seed_hex** |
| 108-110 | Docs, Anti-Sybil pré-filtre, token LoopQA |
| 111 | UX wallet password + session bouton activer |
| 112 | Clarification archi auth/clé privée/API key |
| **113** | **Audit complet sécurité : 9 failles, 6 scénarios attaque** |
| **114** | **TPM EK, hardware identity, GitHub Secrets, anti-fraude** |

---

## PROCHAINES ÉTAPES PRIORITAIRES

### Priorité 1 — Sécurité (rapport 113)

```
[ ] Protéger GET /wallet/list (session optionnelle)
[ ] Rate limiting /auth/login (10/min)
[ ] CORS restreint en production
```

### Priorité 2 — P2P auto-découverte (rapport 114)

```
[ ] ARTCB_NODE_PUBLIC_URL dans .env + config.py
[ ] Bootstrap nodes contacts au démarrage
[ ] Propagation de la liste de pairs (gossip)
```

### Priorité 3 — TPM avancé (rapport 114 → futur)

```
[ ] Créer AK (Attestation Key) depuis l'EK
[ ] Format LVX Hardware Identity Certificate
[ ] Endpoint /node/attest-hardware
[ ] Vérification sur le réseau
```

### Priorité 4 — Mobile (roadmap long terme)

```
[ ] Android ICCID/IMEI fingerprint
[ ] iOS DeviceCheck API
[ ] 1 wallet/SIM
```

---

**Total roadmap : ~85 % complété** (phases 1-5 complètes, phases 6-9 en cours)
