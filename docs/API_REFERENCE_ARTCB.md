# ARTCB — Référence API v0.3.0

Base URL : `http://localhost:8000/api/v1`

---

## Santé

### `GET /health`
```json
{"status": "ok", "debug": true, "chain": {"block_count": 533, "valid": true}}
```

---

## Encode

### `POST /encode`
Encode un texte en graphe IR sémantique.

**Corps :**
```json
{"text": "mon texte", "session_id": "optionnel", "use_llm": false}
```

**Réponse :**
```json
{"graph_id": "g_abc123", "node_count": 5, "edge_count": 3, "compression_ratio": 0.68}
```

> Le `graph_id` retourné peut être utilisé dans `/store`.

---

## Store

### `POST /store`
Grave un graphe IR dans la blockchain comme un bloc.

**Corps — mode 1 : text direct (encode + grave en 1 appel) :**
```json
{"text": "mon texte à encoder et graver"}
```

**Corps — mode 2 : graph_id existant :**
```json
{"graph_id": "g_abc123", "visibility": "private", "wallet_name": "mon_wallet"}
```

**Champs optionnels :**
| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `graph_id` | `string\|null` | `null` | ID du graphe pré-encodé. Obligatoire si `text` absent |
| `text` | `string\|null` | `null` | Texte à auto-encoder. Obligatoire si `graph_id` absent |
| `visibility` | `string` | `"private"` | `private` \| `group` \| `public` |
| `wallet_name` | `string\|null` | `null` | Wallet pour signature et récompense |
| `actor_address` | `string\|null` | `null` | Adresse du validateur |
| `group_id` | `string\|null` | `null` | Requis si `visibility=group` |

**Réponse :**
```json
{
  "block_index": 532,
  "hash": "48df8cc1...",
  "block_reward": 100000000,
  "pol_score": 0.6,
  "graph_id": "g_abc123",
  "visibility": "private",
  "signature": "hybrid:ed25519:...:mldsa65:..."
}
```

---

## Wallet

### `POST /wallet/create`
Crée un nouveau wallet avec clés hybrides Ed25519 + ML-DSA-65.

**Corps :**
```json
{"name": "mon_wallet"}
```

**Réponse :**
```json
{
  "name": "mon_wallet",
  "address": "artcb1...",
  "public_key_hex": "...",
  "public_key_b64": "...",
  "hybrid": true,
  "address_v2": "artcb1pqc..."
}
```

- `hybrid: true` — clés ML-DSA-65 générées (post-quantique)
- `address_v2` — adresse dérivée de la clé PQC (absent si liboqs non installé)

### `GET /wallet/list`
Liste tous les wallets.

### `POST /wallet/balance`
```json
{"address": "artcb1..."}
```

### `GET /wallet/balance/{address}`

---

## Mining Pipeline

### `POST /mining/pipeline`
Pipeline complet : texte → IR → raisonnement dual-agent → bloc PoL.

**Corps :**
```json
{
  "text": "contenu à miner",
  "wallet_name": "mon_wallet",
  "visibility": "private",
  "store_block": true
}
```

> Route asynchrone — non-bloquante. Plusieurs appels simultanés possibles.

---

## Chain

### `GET /chain`
Liste les blocs.

### `GET /chain/block/{index}`
Détail d'un bloc.

### `GET /chain/verify`
Vérification intégrité complète de la chaîne.

---

## P2P

### `GET /p2p/status`
État du nœud P2P (algorithme ML-KEM-768, pairs, blocs publics).

### `POST /p2p/sync`
Synchronisation avec un pair.

---

## PoL Score

### `GET /pol/score`
Score Proof-of-Link courant.

```json
{
  "pol_score": 0.6,
  "delta_compression": 0.68,
  "validation_rate": 1.0,
  "retrieval_accuracy": 1.0
}
```

---

## Notes importantes

| Comportement | Description |
|--------------|-------------|
| Cache encode | Le même texte encodé deux fois retourne le même graphe (cache SHA-256) |
| Anti-Sybil | Rate-limit : 1 bloc par wallet toutes les 60s (configurable `ARTCB_MIN_BLOCK_INTERVAL_SEC`) |
| Signatures hybrides | Chaque bloc signé Ed25519 + ML-DSA-65 simultanément |
| `graph_id` optionnel dans `/store` | Si `text` fourni, l'encode automatique avant gravure |
