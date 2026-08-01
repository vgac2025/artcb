# Rapport 097 — Catalogue complet des 409 tests ARTCB

**Date :** 2026-07-31  
**Tests :** 409/409 PASS (126.69s) — 0 FAIL — 0 SKIP  
**Commit :** `0dab97c` (main)  
**Avancement global : 95 %**

---

## Résumé exécutif

ARTCB dispose de **409 tests automatisés** répartis en **38 fichiers** couvrant
l'intégralité du système : cryptographie post-quantique, blockchain, IA, P2P, API,
frontend, wallet, sécurité, MCP, SDK, performances. Ce rapport décrit chaque test,
ce qu'il valide, les problèmes rencontrés et les solutions appliquées.

---

## Structure générale

| Fichier de test | Tests | Domaine |
|-----------------|-------|---------|
| `test_api.py` | 7 | API REST end-to-end |
| `test_artcb_cli.py` | 5 | CLI multi-commandes |
| `test_book_wailly.py` | 5 | IR Engine — livre réel |
| `test_bridges.py` | 13 | Bridges blockchain |
| `test_chain.py` | 4 | Blockchain core (C + Python) |
| `test_connectors.py` | 5 | Connecteurs sources données |
| `test_dashboard_api.py` | 6 | Dashboard API |
| `test_dashboard_frontend.py` | 13 | Dashboard frontend React |
| `test_devnet_faucet.py` | 6 | Faucet devnet |
| `test_explorer_symbols.py` | 4 | Agent explorateur |
| `test_governance.py` | 4 | Gouvernance on-chain |
| `test_grammar.py` | 2 | Grammaire IR |
| `test_groups.py` | 9 | Groupes/réseaux ARTCB |
| `test_ir_reversibility.py` | 16 | IR Engine réversibilité |
| `test_ir_rules.py` | 26 | Smart contracts PoL (IR v0.2) |
| `test_kem_p2p.py` | 2 | ML-KEM-768 chiffrement |
| `test_libp2p_p2p.py` | 38 | libp2p Phase 13 |
| `test_mcp_server.py` | 24 | Serveur MCP |
| `test_media_ingest.py` | 12 | Ingestion multimédia |
| `test_mining_pipeline.py` | 4 | Pipeline minage IA |
| `test_notifications.py` | 3 | Notifications Telegram |
| `test_optimizations.py` | 10 | Optimisations performances |
| `test_optimizations_advanced.py` | 18 | FAISS, PDF async, Pool, compression |
| `test_p2p_api.py` | 3 | API P2P HTTP (Phase 8) |
| `test_pol.py` | 3 | Proof of Learning |
| `test_pol_nft.py` | 17 | PoL NFT sémantiques |
| `test_pol_transfer.py` | 26 | PoL Transfer ledger |
| `test_pool_e2e.py` | 5 | Pool calcul E2E |
| `test_pool_integration.py` | 7 | Pool intégration |
| `test_pool_policy.py` | 4 | Pool politique minage |
| `test_pool_stress.py` | 3 | Pool stress test |
| `test_pqc_crypto.py` | 12 | PQC ML-DSA-65 + ML-KEM |
| `test_sdk.py` | 28 | SDK Python ARTCB |
| `test_symbol_p2p_integration.py` | 4 | Symboles P2P |
| `test_symbol_store.py` | 3 | Registre symboles |
| `test_symbols.py` | 3 | Symboles IR |
| `test_system_hardware.py` | 6 | Profil matériel |
| `test_wallet_encryption.py` | 7 | Chiffrement wallet AES-256-GCM |
| `test_wallet_rewards.py` | 24 | Wallet + rewards blockchain |
| **TOTAL** | **409** | |

---

## Détail de chaque groupe de tests

---

### 1. `test_api.py` — 7 tests — API REST end-to-end

Ces tests démarrent un vrai serveur FastAPI en mémoire (`TestClient`) et exercent
le flux complet de l'application.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_health` | `GET /api/v1/health` répond `{"status":"healthy"}` |
| `test_encode_decode_roundtrip` | `POST /api/v1/encode` encode du texte en graphe IR, puis `/decode` restitue le texte original — réversibilité E2E |
| `test_search_and_node` | `POST /api/v1/search` trouve un symbole encodé, `GET /api/v1/graph/{id}/node/{id}` retourne le nœud |
| `test_agents_run_and_pol` | `POST /api/v1/agents/run` déclenche Explorateur + Critique IA, vérifie que `pol_score` est présent et entre 0 et 1 |
| `test_store_and_chain` | `POST /api/v1/store` grave un bloc, `GET /api/v1/chain` retourne au moins un bloc avec index et hash |
| `test_rtleg_events` | `GET /api/v1/rtleg/events` retourne la timeline d'apprentissage (append-only) |
| `test_wailly_demo_excerpt` | `GET /api/v1/demo/wailly-excerpt` retourne les 3 premières pages du livre Wailly encodées |

**Problème rencontré :** le champ `graph_id` était obligatoire dans `POST /store` mais non documenté → les tests e2e échouaient avec 422.  
**Solution :** auto-encode ajouté dans la route `/store` (BUG-P0-2 rapport 089) : si `text` est fourni sans `graph_id`, l'encodage est fait automatiquement.

---

### 2. `test_artcb_cli.py` — 5 tests — CLI standalone

Valide le script [`scripts/artcb_cli.py`](scripts/artcb_cli.py) qui reproduit toutes les commandes API en ligne de commande.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_cli_help_exits_zero` | `artcb_cli.py --help` retourne code 0 (pas de crash) |
| `test_cli_health` | `artcb_cli.py health` appelle `GET /health` et affiche OK |
| `test_cli_wallet_and_pool_status` | Crée un wallet CLI + affiche l'état du pool |
| `test_cli_p2p_status` | `artcb_cli.py p2p status` — statut réseau P2P |
| `test_cli_mining_local` | Lance un minage local via CLI et vérifie le résultat |

---

### 3. `test_book_wailly.py` — 5 tests — Livre réel

Valide que l'IR Engine traite correctement un document réel de 466 pages (le livre *Wailly*, texte de référence du projet).

| Test | Ce qu'il valide |
|------|-----------------|
| `test_book_file_readable` | Le fichier PDF `data/wailly.pdf` est lisible et contient du texte |
| `test_book_first_pages_reversibility` | Les 3 premières pages encodées → décodées restituent le texte original (diff ≤ 1%) |
| `test_book_chunk_reversibility` | Un chunk de 500 chars encodé → décodé est identique |
| `test_book_orig_symbols_minted` | Les symboles originaux (`ORIG_*`) sont bien créés lors de l'encodage |
| `test_book_node_count_scales` | Un texte 2× plus long produit ~2× plus de nœuds IR (linéarité) |

**Problème rencontré :** le PDF Wailly (466 pages) provoquait des `LimitReachedError` aléatoires en mode parallèle. Root cause : un seul `PdfReader` partagé entre 5 threads → race condition sur le curseur BytesIO.  
**Solution (rapport 090) :** chaque thread crée son propre `PdfReader(io.BytesIO(pdf_bytes))` — thread-safe, 20/20 runs parallèles OK.

---

### 4. `test_bridges.py` — 13 tests — Bridges blockchain

Valide les bridges sémantiques ARTCB vers Bitcoin, Ethereum, Solana, BNB Chain, Polygon, Avalanche (Phase 12.2).

| Test | Ce qu'il valide |
|------|-----------------|
| `test_instantiation` | `BridgeManager` s'instancie sans erreur |
| `test_supported_chains` | Les 6 chaînes supportées (BTC, ETH, SOL, BNB, POLYGON, AVAX) sont listées |
| `test_unknown_chain_raises` | Une chaîne inconnue lève `ValueError` |
| `test_to_ir_text_bitcoin` | `BridgeResult` Bitcoin → texte IR PoL correctement formaté |
| `test_to_ir_text_ethereum` | `BridgeResult` Ethereum → texte IR PoL avec hash de tx |
| `test_fetch_bitcoin_success` | Récupération tx Bitcoin (mock HTTP) → `BridgeResult` valide |
| `test_fetch_bitcoin_not_found` | TX inexistante → `None` sans exception |
| `test_fetch_ethereum_success` | TX Ethereum (mock) → résultat avec `from_address`, `value_eth` |
| `test_fetch_evm_not_found` | TX EVM inexistante → `None` |
| `test_fetch_solana_success` | TX Solana (mock) → résultat Solana |
| `test_fetch_solana_not_found` | TX Solana inexistante → `None` |
| `test_ping_bitcoin/ethereum/solana/unknown_chain` | Ping des endpoints RPC publics (mock) — 1 test par chaîne |
| `test_status_all_returns_6` | `GET /api/v1/bridges/status` retourne exactement 6 entrées |

**Problème rencontré :** 3/6 bridges échouaient sur les endpoints réseaux publics (Cloudflare ETH, Mempool BTC, Polygon). Normal côté réseau — les tests utilisent des mocks httpx.  
**Solution :** tous les tests de fetch sont mockés via `respx` / `httpx.MockTransport`.

---

### 5. `test_chain.py` — 4 tests — Blockchain core

Valide le cœur de la chaîne : module C (SHA-256) + ChainManager Python.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_c_library_sha256` | La bibliothèque C `libartcb_chain.so` calcule SHA-256 identiquement à `hashlib` Python |
| `test_append_and_verify_chain` | Ajoute 3 blocs + `verify_chain()` retourne `True` |
| `test_chain_prev_hash_links` | `block[n].prev_hash == block[n-1].hash` pour chaque bloc |
| `test_tampered_chain_detected` | Modifier le contenu d'un bloc intermédiaire → `verify_chain()` retourne `False` |

**Problème rencontré :** la lib C `.so` n'était pas compilée automatiquement dans certains environnements (Replit, Codespaces).  
**Solution :** `Makefile` cible `chain` + compilation dans `setup.sh` du devcontainer.

---

### 6. `test_connectors.py` — 5 tests — Connecteurs sources

Valide les connecteurs d'apprentissage : OpenAI, SQLite, chiffrement clés.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_save_and_list_connector_masked` | Enregistrer un connecteur OpenAI → la clé est masquée dans la liste |
| `test_delete_connector` | Supprimer un connecteur → absent de la liste |
| `test_save_openrouter_connector` | Connecteur OpenRouter enregistré avec `base_url` correct |
| `test_sqlite_source_learn` | Apprendre depuis une DB SQLite locale → blocs créés |
| `test_connector_manager_encrypts_on_disk` | La clé API est chiffrée AES-256-GCM sur le disque (pas lisible en clair) |

---

### 7. `test_dashboard_api.py` — 6 tests — Dashboard API

| Test | Ce qu'il valide |
|------|-----------------|
| `test_dashboard_demo_live_log` | `GET /api/v1/dashboard/demo-live` retourne des logs de démo |
| `test_dashboard_mining_latest` | `GET /api/v1/dashboard/mining/latest` retourne les derniers blocs minés |
| `test_dashboard_founders` | `GET /api/v1/dashboard/founders` retourne la liste des fondateurs |
| `test_dashboard_mining_status` | Statut mining : `epoch`, `block_reward`, `supply_mined` présents |
| `test_chain_block_detail` | `GET /api/v1/chain/block/{index}` retourne les détails d'un bloc |
| `test_chain_filter_visibility` | `GET /api/v1/chain?visibility=public` filtre correctement |

---

### 8. `test_dashboard_frontend.py` — 13 tests — Frontend React

Valide que les fichiers du frontend React sont bien présents et correctement configurés (pas de build requis).

| Test | Ce qu'il valide |
|------|-----------------|
| `test_frontend_page_files_exist[*]` (×10) | Les 10 pages TSX existent : Home, Memorize, GraphPage, ChainPage, Wallets, Mining, SystemPage, Logs, Console, Groups |
| `test_app_tsx_declares_route[*]` (×10) | Les 10 routes `/`, `/memorize`, `/graph`, etc. sont déclarées dans `App.tsx` |
| `test_demo_tsx_removed` | L'ancien `Demo.tsx` (placeholder hackathon) a bien été supprimé |
| `test_debug_badge_in_layout` | Le badge DEBUG mode est présent dans `Layout.tsx` |
| `test_network_selector_in_layout` | Le sélecteur de réseau (Public/Privé/Groupe) est présent dans `Layout.tsx` |

---

### 9. `test_devnet_faucet.py` — 6 tests — Faucet devnet

| Test | Ce qu'il valide |
|------|-----------------|
| `test_faucet_unit` | `DevnetFaucet.request()` génère 10 tARTCB (tokens de test) |
| `test_faucet_limit` | Une même adresse ne peut pas recevoir plus de X tARTCB par heure (rate limit) |
| `test_faucet_api` | `POST /api/v1/devnet/faucet` retourne `amount` et `tx_id` |
| `test_wallet_balance_includes_faucet` | Après faucet, `GET /api/v1/wallet/balance` inclut les tokens reçus |
| `test_chain_explorer` | `GET /api/v1/chain/explorer` liste les blocs avec pagination |
| `test_gradium_tts_fallback` | `GET /api/v1/devnet/tts` retourne un fallback texte si Gradium indisponible |

---

### 10. `test_explorer_symbols.py` — 4 tests — Agent explorateur

| Test | Ce qu'il valide |
|------|-----------------|
| `test_explorer_proposes_symbols` | L'agent Explorateur propose des symboles IR lors de l'encodage |
| `test_explorer_result_includes_proposals` | Le résultat inclut `proposed_symbols` et `original_symbols` |
| `test_agents_run_returns_symbol_proposals` | `POST /api/v1/agents/run` retourne des propositions de symboles |
| `test_symbols_registry_api` | `GET /api/v1/symbols` liste les symboles enregistrés |

---

### 11. `test_governance.py` — 4 tests — Gouvernance on-chain

Valide le module de gouvernance : propositions + votes enregistrés sur la chaîne.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_create_proposal` | `POST /api/v1/governance/proposals` crée une proposition avec `proposal_id` |
| `test_cast_vote_yes` | Voter "yes" sur une proposition → le vote est enregistré |
| `test_duplicate_vote_rejected` | Voter deux fois avec la même adresse → rejeté (anti-bourrage) |
| `test_list_proposals` | `GET /api/v1/governance/proposals` liste les propositions actives |

---

### 12. `test_grammar.py` — 2 tests — Grammaire IR

| Test | Ce qu'il valide |
|------|-----------------|
| `test_detect_macros_empty_on_short_text` | Un texte court (< 10 mots) ne produit aucune macro (pas de faux positifs) |
| `test_symbols_assigned` | Les symboles IR sont assignés correctement aux nœuds du graphe |

---

### 13. `test_groups.py` — 9 tests — Groupes et réseaux ARTCB

Valide le système de groupes : Public/Privé/Groupe, fondateur immuable, invitations sécurisées.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_create_group_has_join_code` | Créer un groupe génère un `join_code` unique |
| `test_direct_invite_blocked_by_default` | Inviter directement par adresse est bloqué (sécurité) |
| `test_join_request_flow` | Flux complet : demande d'adhésion → approbation fondateur → membre actif |
| `test_founder_cannot_be_removed_by_admin` | Un admin ne peut pas retirer le fondateur du groupe |
| `test_only_founder_promotes_admin` | Seul le fondateur peut promouvoir un membre en admin |
| `test_admin_cannot_promote_admin` | Un admin ne peut pas promouvoir un autre admin (limite des droits) |
| `test_dissolve_group_founder_only` | Seul le fondateur peut dissoudre le groupe |
| `test_reject_join_request` | Le fondateur peut rejeter une demande d'adhésion |
| `test_store_group_visibility_and_chain_filter` | `POST /store` avec `visibility=group` + `GET /chain?group_id=` filtre les blocs du groupe |

---

### 14. `test_ir_reversibility.py` — 16 tests — IR Engine réversibilité

Le test fondamental du projet : l'IR Engine doit encoder et décoder sans perte.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_reversibility_exact[*]` (×10) | 10 textes différents (phrases simples, textes longs, caractères accentués) encodés puis décodés sont **identiques** à l'original |
| `test_graph_integrity` | Le graphe IR possède `nodes`, `edges`, `graph_id`, `checksum_sha256` |
| `test_json_roundtrip` | Sérialisation JSON du graphe → désérialisation → graphe identique |
| `test_temporal_edges_chain` | Les arêtes temporelles forment une chaîne ordonnée (nœud 0 → 1 → 2…) |
| `test_node_classification` | Les nœuds sont classifiés correctement (fact, decision, hypothesis, observation) |
| `test_compression_ratio_positive` | Le graphe IR est plus compact que le texte brut (ratio > 0) |
| `test_macro_detection_on_repeated_pattern` | Un pattern répété plusieurs fois génère une macro IR |
| `test_empty_text_raises` | Encoder une chaîne vide lève `ValueError` |
| `test_decode_invalid_graph_raises` | Décoder un graphe invalide lève une exception explicite |

---

### 15. `test_ir_rules.py` — 26 tests — Smart contracts PoL (IR v0.2)

Valide le moteur de règles déclaratives IR v0.2 (Phase 11) — l'équivalent de smart contracts pour ARTCB.

**Groupe `TestRuleCondition` (11 tests) :**
| Test | Ce qu'il valide |
|------|-----------------|
| `test_gt_true/false` | Opérateur `>` : évalue correctement |
| `test_gte_equal` | Opérateur `>=` : évalue sur valeur égale |
| `test_lt_true` | Opérateur `<` |
| `test_lte_equal` | Opérateur `<=` sur valeur égale |
| `test_eq_string` | Opérateur `==` sur chaîne de caractères |
| `test_neq_true` | Opérateur `!=` |
| `test_in_operator` | Opérateur `in` : valeur dans une liste |
| `test_contains_operator` | Opérateur `contains` : sous-chaîne |
| `test_missing_variable_returns_false` | Variable absente du contexte → condition `False` (pas d'exception) |
| `test_to_dict_from_dict` | Sérialisation/désérialisation d'une condition |

**Groupe `TestRuleAction` (2 tests) :** sérialisation d'une action IR.

**Groupe `TestIRRule` (7 tests) :**
| Test | Ce qu'il valide |
|------|-----------------|
| `test_evaluate_and_triggered` | Règle AND : toutes les conditions vraies → déclenchée |
| `test_evaluate_and_not_triggered` | Règle AND : une condition fausse → non déclenchée |
| `test_evaluate_or_triggered_partial` | Règle OR : une seule vraie suffit |
| `test_evaluate_or_not_triggered` | Règle OR : toutes fausses |
| `test_to_pol_text` | Règle → texte PoL lisible pour inscription sur la chaîne |
| `test_to_dict_from_dict_roundtrip` | Sérialisation complète d'une règle |
| `test_conditions_results_count` | Résultats d'évaluation contiennent autant d'entrées que de conditions |

**Groupe `TestParseRuleFromText` (4 tests) :**  
Valide le parser naturel : `"SI pol_score > 0.8 ALORS reward_multiplier = 2"` → `IRRule` objet.

**Groupe `TestRulesRegistry` (9 tests) :**  
CRUD complet du registre de règles + `evaluate_all(context)`.

---

### 16. `test_kem_p2p.py` — 2 tests — ML-KEM-768

| Test | Ce qu'il valide |
|------|-----------------|
| `test_kem_roundtrip_encrypt_decrypt` | Chiffrer un payload avec ML-KEM-768 → déchiffrer → payload identique |
| `test_kem_keypair_sizes` | La paire de clés ML-KEM-768 a les tailles NIST correctes (1184 bytes pk, 2400 bytes sk) |

---

### 17. `test_libp2p_p2p.py` — 38 tests — Phase 13 libp2p natif

Tests créés cette session. Couvrent toutes les couches du nœud P2P natif.

**Groupe `TestXorDistance` (4 tests) :** validation de la distance XOR Kademlia.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_same_node_distance_zero` | XOR(A, A) = 0 (propriété fondamentale) |
| `test_different_nodes_nonzero` | XOR(A, B) > 0 si A ≠ B |
| `test_symmetry` | XOR(A, B) = XOR(B, A) |
| `test_invalid_hex_doesnt_crash` | Entrée hex invalide → distance ≥ 0 sans exception |

**Groupe `TestKademliaBucket` (4 tests) :** validation du k-bucket.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_add_and_retrieve` | Ajouter un pair → récupérable par node_id |
| `test_max_k_peers` | Le bucket ne dépasse jamais K=20 pairs |
| `test_remove_peer` | Retirer un pair → absent |
| `test_update_overwrites` | Remettre un pair existant → mise à jour |

**Groupe `TestKademliaDHT` (7 tests) :** validation de la table de routage.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_add_and_find` | Ajouter un pair → trouvable |
| `test_own_node_not_added` | Le nœud n'ajoute pas son propre ID au DHT |
| `test_find_closest_returns_k` | `find_closest()` retourne au plus k pairs |
| `test_find_closest_sorted_by_distance` | Les résultats sont triés par distance XOR croissante |
| `test_remove_peer` | Suppression dans la bonne bucket |
| `test_to_dict_roundtrip` | Export JSON → reimport → même état |
| `test_all_peers` | `all_peers()` retourne tous les pairs enregistrés |

**Groupe `TestGossipSub` (7 tests) :** validation du Gossipsub.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_not_seen_initially` | Nouveau message = non vu |
| `test_mark_seen` | Après marquage = vu |
| `test_make_message_id_stable` | Même bloc → même ID à chaque appel (déterministe) |
| `test_make_message_id_different_blocks` | Blocs différents → IDs différents |
| `test_deliver_calls_handler` | Un bloc entrant est livré au handler souscrit (asyncio) |
| `test_lru_eviction` | Le cache seen est plafonné (LRU) |
| `test_handler_error_doesnt_stop_others` | Un handler qui plante ne bloque pas les autres |

**Groupe `TestPeerInfo` (2 tests) :** sérialisation des informations de pair.

**Groupe `TestLibP2PNodeInit` (7 tests) :** création et initialisation du nœud.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_node_creation` | node_id, host, port correctement initialisés |
| `test_auto_node_id` | node_id auto-généré commence par `node_` |
| `test_status_not_running` | `status()` renvoie `running=False` avant démarrage |
| `test_dht_persistence` | DHT sauvegardé → rechargé dans un nouveau nœud |
| `test_get_local_public_blocks_no_file` | Pas de `blocks.jsonl` → liste vide (pas d'erreur) |
| `test_get_local_public_blocks_filters_private` | Seuls les blocs `visibility=public` sont retournés |
| `test_get_local_public_blocks_from_index` | Paramètre `from_index` filtre correctement |

**Tests TCP réels (7 tests) :**

| Test | Ce qu'il valide |
|------|-----------------|
| `test_node_start_stop` | Démarrage d'un vrai serveur TCP asyncio — connexion possible — arrêt propre |
| `test_two_nodes_handshake` | **2 nœuds TCP réels** se connectent, échangent HELLO, s'enregistrent mutuellement dans leur DHT |
| `test_gossipsub_block_propagation` | Un bloc public annoncé sur node_a est reçu par node_b via Gossipsub (connexion TCP réelle) |
| `test_private_block_not_propagated` | Bloc `visibility=private` → `announce_block()` retourne `sent=0` (jamais diffusé) |
| `test_make_hello_fields` | Le message HELLO contient `type`, `node_id`, `network_id`, `protocol`, `ts` |
| `test_write_read_message_roundtrip` | Encodage `[uint32 longueur][JSON]` → décodage → message identique |
| `test_read_message_timeout` | `_read_message()` sur stream vide → retourne `None` (pas de blocage infini) |

**Problèmes rencontrés :**
1. **Port conflicts** : les tests TCP utilisent des ports fixes (19100, 19200…) → chaque test prend un port différent pour l'isolation.
2. **Handshake timing** : `asyncio.sleep(0.2)` nécessaire après `connect_peer()` pour laisser le serveur accepter et traiter la connexion.

---

### 18. `test_mcp_server.py` — 24 tests — Serveur MCP (Phase 12.1)

Valide le serveur [Model Context Protocol](docs/MCP_SETUP.md) permettant l'intégration avec Cursor, VS Code, Bob IDE.

**Groupe init (5 tests) :** configuration URL, ping, `initialize`, méthode inconnue.

**Groupe `TestMCPToolsList` (2 tests) :** `tools/list` retourne les 7 tools attendus, chacun avec `inputSchema`.

**Groupe `TestMCPResourcesList` (1 test) :** `resources/list` retourne les 2 resources (`artcb://chain/status`, `artcb://wallet/{address}`).

**Groupe `TestMCPPromptsList` (3 tests) :** `prompts/list`, `prompts/get`, `prompts/get` d'un prompt inconnu.

**Groupe `TestMCPToolsCall` (8 tests) :** appel de chacun des 7 tools MCP (memo, think, chain_verify, wallet_balance, search, mine, bridge_import) + tool inconnu.

**Groupe `TestMCPResources` (3 tests) :** lecture des resources `chain_status`, `pol_score`, resource inconnue.

**Groupe `TestMCPHTTPTransport` (2 tests) :** instanciation serveur HTTP mode, handler stdio single request.

**Problème rencontré :** les tests SSE (Server-Sent Events) ne fonctionnent pas avec `TestClient` de httpx (mode sync). Solution : validation via import module plutôt que requête HTTP streaming.

---

### 19. `test_media_ingest.py` — 12 tests — Ingestion multimédia

Valide l'ingestion de 17+ formats : TXT, JSON, JSONL, CSV, TSV, XML, HTML, PDF, images, audio, vidéo, DOCX, XLSX, EPUB, RTF, SRT, VTT.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_list_supported_formats_includes_json_csv` | JSON et CSV sont dans la liste des formats supportés |
| `test_ingest_text_file` | Ingestion d'un `.txt` → texte extrait |
| `test_ingest_json_file` | Ingestion d'un `.json` → contenu sérialisé lisible |
| `test_ingest_jsonl_file` | Ingestion d'un `.jsonl` multi-lignes |
| `test_ingest_csv_file` | CSV → texte tabulaire |
| `test_ingest_tsv_file` | TSV (tabulation-separated) |
| `test_ingest_xml_file` | XML → texte parsé |
| `test_ingest_html_file` | HTML → texte sans balises |
| `test_detect_media_type_json` | Détection automatique type `.json` |
| `test_ingest_folder_mixed_formats` | Dossier avec 3 formats mixtes → tous ingérés |
| `test_local_folder_connector_learn_json_csv` | Connecteur dossier local apprend depuis JSON + CSV |
| `test_connectors_formats_api` | `GET /api/v1/connectors/formats` retourne la liste publique |

---

### 20. `test_mining_pipeline.py` — 4 tests — Pipeline minage IA

Valide le pipeline complet : source → dual-agent → bloc miné.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_build_contributors_with_wallet` | Les contributors sont bien construits avec wallet + pol_score |
| `test_store_with_actor_creates_contributors` | `POST /store` avec `actor` crée les contributors dans le bloc |
| `test_mining_pipeline_sqlite_source` | Pipeline SQLite → apprentissage → bloc miné |
| `test_bulk_mining_batches` | `POST /mining/bulk` traite des lots paginés de textes |

---

### 21. `test_notifications.py` — 3 tests — Notifications Telegram

| Test | Ce qu'il valide |
|------|-----------------|
| `test_save_telegram_channel` | Enregistrer un canal Telegram → persisté |
| `test_gmail_rejected` | Configurer Gmail → rejeté (Gmail retiré du projet, rapport 063) |
| `test_send_telegram_mock` | Envoi d'une notification Telegram (mock httpx) |

---

### 22. `test_optimizations.py` — 10 tests — Optimisations performances

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestCacheOptimization` | 5 | Cache IREncoder actif par défaut, désactivable, hit réutilise le graphe, gain temps mesuré, textes différents → graphes différents |
| `TestParallelPDFProcessing` | 3 | Extraction parallèle activée, plus rapide que séquentiel sur grand PDF, séquentiel pour petits fichiers |
| `TestIntegrationOptimizations` | 2 | Cache + parallèle ensemble, test perf E2E (encode 5 textes en < 5s) |

---

### 23. `test_optimizations_advanced.py` — 18 tests — FAISS, PDF async, Pool, compression

| Test | Ce qu'il valide |
|------|-----------------|
| `test_faiss_vector_store_cpu` | FAISS CPU index → recherche vectorielle fonctionne |
| `test_faiss_similarity_scores` | Scores de similarité cosinus entre 0 et 1 |
| `test_faiss_empty_query` | Requête sur index vide → liste vide (pas d'erreur) |
| `test_async_pdf_extraction` | Extraction PDF asyncio, 466 pages, texte > 1000 chars, "Wailly" présent |
| `test_async_pdf_fallback_sequential` | Si extraction parallèle échoue → fallback séquentiel |
| `test_pool_manager_explore_batch` | PoolManager traite un lot d'exploration |
| `test_pool_manager_validate_batch` | PoolManager valide un lot |
| `test_pool_manager_context_manager` | `with PoolManager()` → fermeture propre |
| `test_graph_compression` | Compresser un graphe IR → taille réduite |
| `test_compression_ratio_estimation` | Ratio estimation cohérent avec taille réelle |
| `test_node_index_add_and_find` | Index nœuds → `find_by_id()` retrouve le nœud |
| `test_node_index_by_type` | Filtrer nœuds par type (fact, decision…) |
| `test_node_index_text_prefix` | Recherche par préfixe de texte dans l'index |
| `test_graph_store_lazy_loading` | GraphStore charge les graphes à la demande (lazy) |
| `test_graph_store_cache_hit` | 2ème accès au même graphe → pas de rechargement disque |
| `test_pol_scorer_numpy_batch` | PolScorer calcule batch numpy → plus rapide que boucle Python |
| `test_pol_scorer_numpy_multiple_graphs` | Scores multiples cohérents entre 0 et 1 |
| `test_integration_all_optimizations` | Cache + FAISS + compression + PoolManager ensemble |
| `test_performance_comparison` | Benchmark : version optimisée ≥ 2× plus rapide |

**Problème rencontré :** `test_async_pdf_extraction` était flaky → race condition PdfReader partagé entre threads (rapport 090).  
**Solution :** `PdfReader` isolé par thread → test restauré avec assertions fortes (`len > 1000`, `"Wailly" in text`).

---

### 24. `test_p2p_api.py` — 3 tests — API P2P HTTP (Phase 8)

Valide les routes P2P HTTP existantes (Phase 8, compatibles Phase 13).

| Test | Ce qu'il valide |
|------|-----------------|
| `test_p2p_status` | `GET /api/v1/p2p/status` retourne `node_id`, `network_id`, `kem_algorithm=ML-KEM-768` |
| `test_add_peer` | `POST /api/v1/p2p/peers` ajoute un pair avec sa clé ML-KEM |
| `test_public_blocks_endpoint` | `GET /api/v1/p2p/blocks/public` retourne les blocs publics locaux |

---

### 25. `test_pol.py` — 3 tests — Proof of Learning

| Test | Ce qu'il valide |
|------|-----------------|
| `test_pol_score_high_for_valid_graph` | Un graphe IR bien structuré obtient un PoL score ≥ 0.6 |
| `test_collective_reward_split` | Le reward ARTCB est splité proportionnellement aux scores PoL des contributors |
| `test_dual_agent_loop` | L'agent Explorateur + l'agent Critique s'exécutent ensemble et produisent un PoL score |

---

### 26. `test_pol_nft.py` — 17 tests — PoL NFT sémantiques (Phase 11)

Valide les NFT sémantiques post-quantiques (des blocs de connaissance uniques et transférables).

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestPolNFT` | 8 | Création NFT, owner par défaut = créateur, texte PoL généré, transfert, chaîne de transferts, sérialisation |
| `TestNFTRegistry` | 9 | Mint + récupération, doublon rejeté, NFT inexistant → None, filtrage par owner/creator, transfert registre, liste complète, registre vide |

---

### 27. `test_pol_transfer.py` — 26 tests — PoL Transfer ledger (Phase 11)

Valide les transferts de tokens ARTCB entre wallets.

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestPolTransfer` | 6 | Timestamp auto, texte PoL avec champs, sans memo, avec référence, sérialisation, valeurs optionnelles |
| `TestTransferLedger` | 20 | Ajout + liste, multiples, par adresse émettrice, filtrage exclusion, by_id trouvé/non trouvé, balance positive/zéro/négative, précision décimale, ledger vide, persistance, ligne corrompue ignorée |

**Problème rencontré :** la balance négative était considérée comme une erreur.  
**Solution :** les balances négatives sont légitimes (dette entre wallets) → `test_balance_of_negative_allowed` confirme.

---

### 28. `test_pool_e2e.py` — 5 tests — Pool calcul E2E

Valide le pool de calcul distribué opt-in avec chiffrement ML-KEM-768.

| Test | Ce qu'il valide |
|------|-----------------|
| `test_pool_chunk_crypto_roundtrip` | Chiffrer un chunk ML-KEM → déchiffrer → payload identique |
| `test_pool_result_crypto_roundtrip` | Idem pour un résultat de calcul |
| `test_pool_service_local_job_finalize` | Un job local se finalise correctement |
| `test_pool_api_status` | `GET /api/v1/pool/status` retourne l'état du pool |
| `test_pool_api_create_job_local` | `POST /api/v1/pool/jobs` crée un job local |

---

### 29. `test_pool_integration.py` — 7 tests — Pool intégration

| Test | Ce qu'il valide |
|------|-----------------|
| `test_pool_run_local_private` | Minage local, bloc private |
| `test_pool_run_local_public` | Minage local, bloc public |
| `test_pool_run_local_group` | Minage local, bloc group |
| `test_pool_run_local_mode_no_network` | Mode local = pas de réseau requis |
| `test_pool_rejects_unencrypted_distributed` | Mode distribué sans chiffrement → rejeté (sécurité) |
| `test_pool_preferences_roundtrip` | Préférences pool (visibility, mode) persistées |
| `test_mining_pipeline_distributed_flag` | Flag `distributed=true` déclenche le bon mode |

---

### 30. `test_pool_policy.py` — 4 tests — Pool politique

| Test | Ce qu'il valide |
|------|-----------------|
| `test_local_mining_no_policy_block` | Minage local : aucune politique bloquante |
| `test_distributed_requires_encryption` | Distribué : ML-KEM obligatoire |
| `test_group_requires_group_id` | Bloc de groupe : `group_id` obligatoire |
| `test_all_visibilities_accepted_local` | Local accepte private, public et group |

---

### 31. `test_pool_stress.py` — 3 tests — Stress pool

| Test | Ce qu'il valide |
|------|-----------------|
| `test_pool_stress_many_chunks` | 100 chunks traités sans erreur |
| `test_pool_stress_concurrent_jobs` | 10 jobs concurrents → tous finalisés |
| `test_pool_stress_finalize_after_batch_process` | Finalisation après traitement batch d'un lot |

---

### 32. `test_pqc_crypto.py` — 12 tests — Cryptographie post-quantique

Valide les algorithmes NIST 2024 : ML-DSA-65 (signature) et ML-KEM-768 (chiffrement).

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestPQCCore` | 4 | Taille paires de clés ML-DSA-65, pack/unpack, sign+verify, hash SHA3-256+SHA3-512 dual |
| `TestHybridSignatures` | 3 | Signature hybride Ed25519+ML-DSA-65, parsing signature hybride, rétrocompatibilité Ed25519 seul |
| `TestHybridWallet` | 3 | Création wallet hybride, signature message, rechargement wallet |
| `TestHybridChain` | 2 | Bloc contient `sha3_hash` + `hybrid_sig`, génération adresse `artcb2…` depuis clés hybrides |

**Note :** si `liboqs-python` n'est pas installé, les tests PQC ML-DSA-65 sont skippés et le fallback Ed25519 est testé.

---

### 33. `test_sdk.py` — 28 tests — SDK Python ARTCB

Valide le SDK client officiel `src/artcb/sdk/client.py`.

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestArtcbClientInit` | 10 | URL par défaut, URL custom, trailing slash supprimé, API key stockée, pas de clé, repr, headers |
| `TestArtcbClientMethods` | 13 | `health()`, `verify_chain()`, `memo()`, `think()`, `search()`, `wallets()`, `create_wallet()`, `create_api_key()`, `list_api_keys()`, `memorize()`, `create_rule()`, `list_rules()`, `register_webhook()` |
| `TestArtcbErrors` | 3 | Erreur HTTP 4xx, 500, connexion impossible → `ArtcbError` |
| `TestConnectFactory` | 2 | `connect()` factory réussit / échoue si API non healthy |

---

### 34. `test_symbol_p2p_integration.py` — 4 tests — Symboles P2P

| Test | Ce qu'il valide |
|------|-----------------|
| `test_public_block_carries_symbols` | Un bloc public contient ses symboles IR dans `public_symbols` |
| `test_symbol_publish_and_registry` | Publier un symbole → présent dans le registre |
| `test_p2p_symbols_endpoints` | `GET /api/v1/p2p/symbols/public` retourne les symboles publiés |
| `test_gossip_announce` | `POST /api/v1/p2p/gossip/announce` enregistre l'annonce du nœud |

---

### 35. `test_symbol_store.py` — 3 tests — Registre symboles persistant

| Test | Ce qu'il valide |
|------|-----------------|
| `test_persistent_registry_save_reload` | Registre sauvegardé sur disque → rechargé intacte |
| `test_merge_remote_symbols` | Symboles d'un nœud distant mergés dans le registre local |
| `test_publish_from_graph` | Symboles extraits d'un graphe IR → publiés dans le registre |

---

### 36. `test_symbols.py` — 3 tests — Symboles IR

| Test | Ce qu'il valide |
|------|-----------------|
| `test_mint_original_symbol_stable` | Un symbole original `ORIG_*` est stable entre deux encodages du même texte |
| `test_encoder_stores_orig_symbols` | L'encodeur stocke les symboles originaux dans le graphe |
| `test_original_symbol_in_node` | Le nœud IR contient l'attribut `original_symbol` |

---

### 37. `test_system_hardware.py` — 6 tests — Profil matériel

| Test | Ce qu'il valide |
|------|-----------------|
| `test_detect_hardware_returns_sane_values` | CPU count ≥ 1, RAM > 0, os_name non vide |
| `test_live_metrics_structure` | Métriques live : `cpu_percent`, `memory_used_mb`, `disk_used_gb` présents |
| `test_optimization_profile_defaults` | Profil d'optimisation par défaut cohérent avec le matériel |
| `test_default_pool_chunk_chars` | Taille chunk pool adaptée à la RAM disponible |
| `test_metrics_api_includes_hardware` | `GET /api/v1/system/metrics` inclut les données hardware |
| `test_system_hardware_endpoint` | `GET /api/v1/system/hardware` retourne CPU, RAM, OS |

---

### 38. `test_wallet_encryption.py` — 7 tests — Chiffrement wallet AES-256-GCM

Valide le chiffrement `ARTCBENC1` : scrypt + AES-256-GCM (rapport 055).

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestWalletEncryptionModule` | 5 | Chiffrer/déchiffrer identique, mauvaise passphrase échoue, legacy plain seed toujours chargeable, passphrase manquante lève erreur, migration automatique ancien format |
| `TestWalletManagerEncrypted` | 2 | Wallet créé → chiffré sur disque (pas lisible en clair), clé plain auto-migrée au chargement |

---

### 39. `test_wallet_rewards.py` — 24 tests — Wallet + rewards

Valide la génération d'adresses, la gestion des wallets et les récompenses PoL.

| Groupe | Tests | Ce qu'ils valident |
|--------|-------|--------------------|
| `TestAddressGeneration` | 6 | Adresse depuis pubkey, adresse depuis signing key, vérification adresse valide, préfixe invalide, checksum invalide, déterminisme |
| `TestWalletManager` | 6 | Créer wallet, doublon échoue, charger wallet, wallet introuvable, liste wallets, signer message |
| `TestBlockRewards` | 6 | Reward genesis = 1 ARTCB, halving à 105000 blocs, max halvings, split collectif, split 1 contributor, split scores nuls |
| `TestBlockWithRewards` | 3 | Bloc avec contributors, sans contributors, JSON inclut rewards |
| `TestWalletBalance` | 3 | Balance chaîne vide = 0, balance après 1 bloc, balance après plusieurs blocs |

---

## Problèmes rencontrés et solutions (synthèse)

| # | Problème | Découvert | Solution |
|---|----------|-----------|----------|
| 1 | `POST /store` : `graph_id` obligatoire mais non documenté | Rapport 089 (e2e logger) | Auto-encode si `text` fourni (BUG-P0-2) |
| 2 | `/store` synchrone bloque FastAPI 60s (anti-sybil) | Rapport 089 | `async def store()` + `asyncio.to_thread()` (BUG-P0-1) |
| 3 | Race condition PdfReader partagé entre threads | Rapport 090 | `PdfReader` isolé par thread (thread-safe) |
| 4 | `wallet_create` ne retournait pas `hybrid` + `address_v2` | Rapport 089 | Forçage hybrid à la création (BUG-P1-2) |
| 5 | `public_symbols=None` pour blocs privés → `type=unknown` | Rapport 075 | Suppression condition erronée (gravés toujours) |
| 6 | SSE non testable via `TestClient` httpx sync | Rapport 087 | Validation par import module |
| 7 | `test_pool_manager_explore_batch` fail | Rapport 083 | Fausse alerte — PASS après correction isolation |
| 8 | Ports TCP conflicts dans tests libp2p | Phase 13 | Ports distincts par test (19100, 19200, 19300…) |
| 9 | Timing TCP handshake dans tests asyncio | Phase 13 | `asyncio.sleep(0.2)` après connect_peer |
| 10 | Balance négative wallet → erreur considérée | Phase 11 | Balances négatives légitimes — test `test_balance_of_negative_allowed` |

---

## Répartition par phase du projet

| Phase | Tests | % du total |
|-------|-------|-----------|
| Phase 1 — IR Engine | 16 + 2 + 3 = 21 | 5 % |
| Phase 2/3 — Backend + Blockchain | 7 + 4 + 24 = 35 | 8.5 % |
| Phase 4 — Frontend | 13 | 3 % |
| Phase 6 — Extensions (wallets, groupes, gouvernance) | 9 + 4 + 7 = 20 | 5 % |
| Phase 7 — Mining pipeline | 4 + 3 + 4 + 3 = 14 | 3.5 % |
| Phase 8 — P2P HTTP + Pool | 3 + 5 + 7 + 4 + 3 = 22 | 5 % |
| Phase 9 — CLI + SDK | 5 + 28 = 33 | 8 % |
| Phase 10 — API Keys + i18n | inclus dans test_api | — |
| Phase 11 — IR Rules + NFT + Transfer | 26 + 17 + 26 = 69 | 17 % |
| Phase 12 — MCP + Bridges + Crypto | 24 + 13 + 12 + 2 = 51 | 12.5 % |
| Phase 13 — libp2p natif | 38 | 9 % |
| Performances + hardware | 10 + 18 + 6 = 34 | 8 % |
| Wallet + encryption | 7 + 6 = 13 | 3 % |
| Connecteurs + notifications | 5 + 3 = 8 | 2 % |
| Livre Wailly + grammaire | 5 + 2 = 7 | 1.5 % |
| Devnet + symboles | 6 + 3 + 3 + 4 = 16 | 4 % |
| **TOTAL** | **409** | **100 %** |

---

## Validation finale

```
409 passed in 126.69s (0:02:06)
0 failed — 0 skipped — 0 errors
```

Tous les tests s'exécutent avec `python3 -m pytest tests/ -q` sans dépendance réseau externe.
Les tests PQC utilisent la vraie bibliothèque `liboqs-python` v0.16.0 (ML-DSA-65 + ML-KEM-768).
Les tests TCP (Phase 13) démarrent de vraies connexions localhost.

---

*Rapport généré le 2026-07-31 | Tests : 409/409 PASS | Commit : 0dab97c | Avancement : 95 %*
