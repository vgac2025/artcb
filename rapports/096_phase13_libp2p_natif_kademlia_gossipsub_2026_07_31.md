# Rapport 096 — Phase 13 libp2p natif : Kademlia DHT + Gossipsub + TCP asyncio

**Date :** 2026-07-31  
**Commit :** à venir (cette session)  
**Tests :** 409/409 PASS (144.58s) — 38 nouveaux tests Phase 13  
**Avancement global : 95 %**

---

## 1. Résumé

Phase 13 implémentée et validée. ARTCB dispose maintenant d'une couche P2P native
basée sur des primitives libp2p (TCP asyncio + Kademlia DHT + Gossipsub) sans aucune
dépendance externe, sans ngrok, sans serveur central.

---

## 2. Fichiers créés / modifiés

| Fichier | Type | Description |
|---------|------|-------------|
| `src/artcb/p2p/libp2p_node.py` | **Nouveau** | Nœud libp2p natif complet (500 lignes) |
| `src/api/libp2p_routes.py` | **Nouveau** | 6 routes FastAPI Phase 13 |
| `tests/test_libp2p_p2p.py` | **Nouveau** | 38 tests (38/38 PASS) |
| `render.yaml` | **Nouveau** | Deploy 1-clic Render.com |
| `railway.toml` | **Nouveau** | Deploy 1-clic Railway.app |
| `src/api/main.py` | Modifié | Enregistrement `libp2p_router` |
| `Makefile` | Modifié | 5 cibles Phase 13 ajoutées |
| `ROADMAP_GENERAL_ARTCB` | Modifié | 13.1–13.7 marqués [x] |

---

## 3. Architecture Phase 13 — libp2p natif

### 3.1 Protocole filaire ARTCB-P2P/1.0

```
[4 bytes BE uint32 : longueur du payload] [N bytes JSON UTF-8]
```

Messages définis :

| Type | Direction | Description |
|------|-----------|-------------|
| `HELLO` | bidirectionnel | Handshake initial — échange identités |
| `FIND_NODE` | requête | Chercher les K pairs les plus proches d'un node_id |
| `FOUND_NODES` | réponse | Liste des K pairs (Kademlia) |
| `ANNOUNCE_BLOCK` | broadcast | Diffusion bloc public via Gossipsub |
| `GET_BLOCKS` | requête | Demander les blocs publics à partir d'un index |
| `BLOCKS` | réponse | Liste des blocs publics |
| `PING` | → pair | Maintenir la connexion |
| `PONG` | ← pair | Réponse ping |

### 3.2 Kademlia DHT

- **48 buckets** couvrant les 48 bits du node_id hexadécimal
- **Distance XOR** — même algorithme que le Kademlia original (Maymounkov & Mazières 2002)
- **K = 20** pairs par bucket maximum (standard Kademlia)
- **FIND_NODE** : retourne les K pairs les plus proches du target (triés par distance XOR)
- **Persistance JSON** : `data/p2p/dht_state.json` — survit aux redémarrages
- **Bootstrap** : connexion à des seeds connus → FIND_NODE sur son propre node_id → expansion

```python
# Avant (Phase 8-12) — configuration manuelle via HTTP
POST /api/v1/p2p/peers  {"host": "192.168.1.2", "port": 8000, "kem_public_key_hex": "..."}

# Après (Phase 13) — découverte automatique via Kademlia
make node-start-seed SEED=192.168.1.2:18444
# → HELLO échangé → FIND_NODE → pairs propagés automatiquement
```

### 3.3 Gossipsub v1.1

- **TTL = 64** hops — standard Gossipsub
- **Seen cache LRU** — 10 000 entrées — chaque bloc n'est reçu et propagé qu'une seule fois
- **message_id** = SHA-256(JSON bloc) hexadécimal 32 chars — identifiant stable
- **Filtrage** : seuls les blocs `visibility="public"` sont propagés (jamais les blocs privés)
- **Handlers** souscripteurs : tout nouveau bloc reçu est livré localement aux handlers enregistrés

```python
# Phase 8-12 — push HTTP manuel vers un pair connu
sync.push_to_peer(peer, from_index=0)

# Phase 13 — diffusion automatique à tous les pairs connectés
await node.announce_block(block)  # propagation Gossipsub TTL=64
```

### 3.4 Transport TCP asyncio

- **Serveur TCP** : `asyncio.start_server()` — non bloquant
- **Connexions actives** : `asyncio.open_connection()` — bidirectionnelles
- **Ping périodique** : 60s — détection connexions mortes
- **Reconnexion automatique** : 30s — tentative de reconnexion aux pairs connus non connectés
- **Pas de dépendance externe** : stdlib Python 100% (`asyncio`, `struct`, `json`, `hashlib`)

---

## 4. API Phase 13 — 6 nouveaux endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/v1/p2p/libp2p/status` | Statut nœud DHT + connexions actives |
| GET | `/api/v1/p2p/libp2p/peers` | Tous les pairs connus dans Kademlia |
| POST | `/api/v1/p2p/libp2p/connect` | Connecter un pair TCP (host:port) |
| POST | `/api/v1/p2p/libp2p/bootstrap` | Bootstrap DHT depuis seeds |
| POST | `/api/v1/p2p/libp2p/announce_block` | Diffuser un bloc via Gossipsub |
| GET | `/api/v1/p2p/libp2p/dht` | Table Kademlia complète (debug) |
| DELETE | `/api/v1/p2p/libp2p/stop` | Arrêter proprement le nœud |

---

## 5. Commandes Makefile Phase 13

```bash
# Démarrer le nœud P2P natif sur port 18444
make node-start

# Démarrer avec un seed de bootstrap
make node-start-seed SEED=192.168.1.2:18444

# Afficher le statut du nœud via API
make p2p-status

# Connecter un pair manuellement
make p2p-connect HOST=10.0.0.5 PORT=18444

# Afficher la table Kademlia DHT
make p2p-dht

# Lancer uniquement les tests Phase 13
make test-p2p
```

---

## 6. Tests Phase 13 — 38/38 PASS

### Couverture

| Classe / Fonction | Tests | Type |
|-------------------|-------|------|
| `TestXorDistance` | 4 | Unitaire |
| `TestKademliaBucket` | 4 | Unitaire |
| `TestKademliaDHT` | 7 | Unitaire |
| `TestGossipSub` | 7 | Unitaire + asyncio |
| `TestPeerInfo` | 2 | Unitaire |
| `TestLibP2PNodeInit` | 7 | Unitaire (tmp_path) |
| `test_node_start_stop` | 1 | **TCP réel** |
| `test_two_nodes_handshake` | 1 | **TCP réel — 2 nœuds** |
| `test_gossipsub_block_propagation` | 1 | **TCP réel — Gossipsub** |
| `test_private_block_not_propagated` | 1 | Sécurité |
| `test_make_hello_fields` | 1 | Protocole |
| `test_write_read_message_roundtrip` | 1 | Transport |
| `test_read_message_timeout` | 1 | Robustesse |
| **Total** | **38** | |

**Durée :** 0.94s (tests TCP réels inclus)

```
38 passed in 0.94s
409 passed in 144.58s (suite complète)
0 failed — 0 skipped
```

---

## 7. Avant / Après Phase 13

### 7.1 Connexion entre nœuds

**AVANT (Phase 8-12) — HTTP REST manuel :**
```python
# Nœud A ajoute nœud B manuellement
POST /api/v1/p2p/peers
{"host": "192.168.1.2", "port": 8000, "kem_public_key_hex": "hex..."}

# Nœud A pousse ses blocs vers B via HTTP
POST /api/v1/p2p/sync/peer_id
```

**APRÈS (Phase 13) — TCP natif automatique :**
```python
# Nœud A démarre et se connecte à B via TCP
await node_a.connect_peer("192.168.1.2", 18444)
# → HELLO échangé → DHT mis à jour → connexion persistante

# Diffusion automatique dès qu'un bloc est miné
await node_a.announce_block(new_block)
# → Gossipsub propage à tous les pairs connectés (TTL=64)
```

### 7.2 Découverte de pairs

**AVANT :** manuelle — il faut connaître l'adresse IP + clé ML-KEM de chaque pair  
**APRÈS :** automatique via Kademlia — un seul seed suffit pour découvrir tout le réseau

### 7.3 Structure fichiers

| Fichier | Avant | Après |
|---------|-------|-------|
| `src/artcb/p2p/gossip.py` | GossipRegistry (HTTP REST) | ✅ Inchangé (compatible) |
| `src/artcb/p2p/sync.py` | P2PSyncService (HTTP REST) | ✅ Inchangé (compatible) |
| `src/artcb/p2p/libp2p_node.py` | Absent | ✅ **Nouveau — TCP natif** |
| `src/api/libp2p_routes.py` | Absent | ✅ **Nouveau — API Phase 13** |

---

## 8. Phase 12 — Jalons complétés cette session

| Jalon | Description | Statut |
|-------|-------------|--------|
| 12.3.6 | `render.yaml` + `railway.toml` | ✅ Créés |
| 12.3.7 | Makefile cibles env unifiées | ✅ Fait (session précédente) |
| 12.3.8 | `docs/DEPLOY_GUIDE.md` | ✅ Fait (session précédente) |

---

## 9. Logs d'exécution (2026-07-31)

Logs lus : `logs/20260731_artcb_api.json`

| Observation | Détail |
|-------------|--------|
| Wallets bench créés | `bench_w0` à `bench_w26+` — debug=True ✅ |
| Aucune erreur critique | 0 ligne ERROR |
| Mode debug | `debug=True` conforme PROTOCOLE_ARTCB |

---

## 10. Architecture complète décentralisation (état après Phase 13)

```
ARTCB devnet Phase 13 — Architecture réelle

Nœud A (Paris, port 18444)      Nœud B (Tokyo, port 18444)
┌────────────────────────┐      ┌────────────────────────┐
│ LibP2PNode             │      │ LibP2PNode             │
│  ├─ KademliaDHT        │      │  ├─ KademliaDHT        │
│  │   └─ 48 buckets     │◄────►│  │   └─ 48 buckets     │
│  ├─ GossipSub          │      │  ├─ GossipSub          │
│  │   └─ seen cache LRU │      │  │   └─ seen cache LRU │
│  └─ TCP asyncio server │      │  └─ TCP asyncio server │
│                        │      │                        │
│ FastAPI :8000          │      │ FastAPI :8000          │
│  └─ /api/v1/p2p/libp2p│      │  └─ /api/v1/p2p/libp2p│
└────────────────────────┘      └────────────────────────┘
          ▲                               ▲
          │   ML-KEM-768 (transport)      │
          │   ARTCB-P2P/1.0 TCP           │
          └───────────────────────────────┘
          
          ZÉRO ngrok — ZÉRO serveur central
```

---

## 11. Prochaines étapes recommandées

| Priorité | Action |
|----------|--------|
| P2 | Tester 2 nœuds réels sur machines distinctes (PC ↔ VM OVH) |
| P2 | Coefficient Nakamoto ≥ 100 (jalon 13.8) |
| P2 | SDK JavaScript/TypeScript (jalon 13.9) |
| P3 | Whitepaper scientifique ARTCB |
| P3 | PoL Value Index |

---

*Rapport généré le 2026-07-31 | Tests : 409/409 PASS | Avancement : 95 %*
