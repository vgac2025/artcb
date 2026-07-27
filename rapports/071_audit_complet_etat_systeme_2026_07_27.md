# Rapport 071 — Audit Complet État Système ARTCB
**Date :** 2026-07-27  
**Agent :** Bob (IBM)  
**Branche :** `main` @ `1352879`  
**Avancement global estimé : 72 %**

---

## 1. RÉSUMÉ EXÉCUTIF

| Domaine | État | % |
|---------|------|---|
| Backend API (routes, chain, wallet, mining) | ✅ Opérationnel | 100 % |
| Blockchain (chaîne valide, ML-DSA-65, C natif) | ✅ 34 blocs valides | 100 % |
| Tests pytest | ⚠️ 1 test en échec / 234 | 99.5 % |
| Frontend i18n (traductions multilingues) | ❌ **0 % pages traduites** | ~10 % |
| Module API Keys utilisateur (ChatGPT/externe) | ❌ **Non implémenté** | 0 % |
| Replay QA | ✅ 24 journeys, 0 bugs open | ~85 % |
| WatsonX | ⚠️ IAM OK, project_id manquant | 40 % |
| Connecteur Cursor LLM | ⚠️ Clé valide, pas d'endpoint REST | 50 % |

---

## 2. PROTOCOLE — CONFORMITÉ

### Fichiers de référence (PROTOCOLE_ARTCB)

| Fichier | Existe | À jour |
|---------|--------|--------|
| `PROTOCOLE_ARTCB` | ✅ | Oui |
| `AUTO_PROMPT_ARTCB` | ✅ | Dernière entrée 2026-07-09T01:35 |
| `ROADMAP_GENERAL_ARTCB` | ✅ | Phase 9 ✅, Phase 10 partielle |
| `CAHIER_DES_CHARGES_ARTCB` | ✅ v1.4 | OK |
| `API_REFERENCE_ARTCB.md` | ✅ ~70 routes | OK |
| `LISTE_TESTS_ARTCB.md` | ✅ 210 tests listés | ⚠️ 234 réels vs 210 listés |
| `LEÇONS_APPRISES_ARTCB` | ✅ | OK |
| `INDEX_ARTCB` | ✅ | Pas mis à jour depuis rapport 067 |

**Écarts détectés :**
- `AUTO_PROMPT_ARTCB` : pas mis à jour depuis juillet 2026 (session ngrok, WatsonX, Wikipedia, Cursor non documentés)
- `LISTE_TESTS_ARTCB.md` : 234 tests réels vs 210 listés → **24 tests non documentés**
- `ROADMAP_GENERAL_ARTCB` : modules ajoutés (watsonx, cursor, ngrok, slashing, symbols) non planifiés

---

## 3. ROADMAP — ÉTAT DES PHASES

### Phases complétées ✅
| Phase | Description | Commits |
|-------|-------------|---------|
| 0–4 | Spécification, IR Engine, Backend, Blockchain, Frontend | Juillet 2026 |
| 6 | Connecteurs IA + DB | `ff47518`, `dac9b19` |
| 7 | Pipeline minage apprentissage + raisonnement | `99ce08e` |
| 8 | P2P ML-KEM + multimodal + gouvernance | `e4ddf79` |
| 9 | Pool E2E + CLI + API/CLI complet | `191274d` |

### Phases partielles ⏳
| Phase | Item | État | Bloquant |
|-------|------|------|----------|
| 3.6 | Faucet tARTCB devnet | `/api/v1/devnet/faucet` existe mais simulé | Non |
| 10 | libp2p natif | HTTP gossip uniquement | Non |
| **NOUVEAU** | **i18n traductions complètes** | 10 % seulement | **Oui** |
| **NOUVEAU** | **Module API Keys public** | 0 % | **Oui** |
| **NOUVEAU** | **WatsonX project_id** | IAM OK, pas de projet | Non |

### Non planifié mais implémenté ✅
| Module | Commit | Note |
|--------|--------|------|
| Anti-Sybil validator + Slashing | `e4ddf79` | Non dans ROADMAP |
| ML-DSA-65 hybride (PQC) | `4c720b6` | ROADMAP disait "future" |
| Symbols sync P2P | `99ce08e` | Extension Phase 8 |
| Ngrok auto-restart logic | Session courante | Infrastructure |
| Replay QA intégration | Session courante | Non planifié |
| Wikipedia connector (prévu) | Non fait | Mentionné session précédente |

---

## 4. BUG CRITIQUE — i18n TRADUCTIONS

### État réel (audit code 2026-07-27)

| Fichier | useTranslation | ~textes hardcodés |
|---------|---------------|-------------------|
| `DashboardLayout.tsx` | ✅ OUI | ~0 |
| `ChainPage.tsx` | ❌ NON | ~7 |
| `Console.tsx` | ❌ NON | ~2 |
| `Governance.tsx` | ❌ NON | ~5 |
| `GraphPage.tsx` | ❌ NON | ~4 |
| `Groups.tsx` | ❌ NON | ~5 |
| `Home.tsx` | ❌ NON | ~4 |
| `Integrations.tsx` | ❌ NON | ~13 |
| `JoinGroup.tsx` | ❌ NON | ~3 |
| `Memorize.tsx` | ❌ NON | ~5 |
| `Mining.tsx` | ❌ NON | ~3 |
| `Network.tsx` | ❌ NON | ~9 |
| `Wallets.tsx` | ❌ NON | ~5 |
| `SystemMetrics.tsx` | ❌ NON | ~4 |
| `Reconstruct.tsx` | ❌ NON | ~2 |

**Résultat :** 14/15 pages n'utilisent PAS `useTranslation()`.  
Le sélecteur de langue change la préférence stockée **mais aucune page ne l'applique**.

### État du fichier `translations.ts`

| Élément | Valeur |
|---------|--------|
| Clés dans l'interface TypeScript | 238 |
| Clés en FR | 56 (23 % de l'interface) |
| Clés en EN | 56 (23 %) |
| Clés en ZH/ES/PT/IT/RU | 45 chacune (19 %) |
| Pages utilisant `t()` | 0 |

**Cause racine :** La refonte i18n (rapport 059–060) a étendu l'interface à 238 clés mais :
1. N'a rempli que 56/238 clés en FR et EN
2. N'a modifié aucune page pour importer `useTranslation`
3. Les 7 langues n'ont que 19–23 % des traductions nécessaires

### Impact
Quand l'utilisateur change la langue dans le sélecteur → **rien ne change** dans les pages car elles n'appellent pas `t()`.

---

## 5. FONCTIONNALITÉ MANQUANTE — MODULE API KEYS PUBLIC

### Description
L'utilisateur souhaite que les développeurs tiers (ChatGPT, autres plateformes) puissent interagir avec la blockchain ARTCB via une **clé API personnelle**. 

**Ce qui existe aujourd'hui :**
- Connecteurs LLM internes (stockage local chiffré `data/connectors/`)
- Pas de système de tokens/clés API d'accès pour utilisateurs externes
- Pas d'endpoint d'authentification par token Bearer externe
- Pas de gestion utilisateurs/comptes

**Ce qui manque :**
```
POST /api/v1/api-keys/generate   → génère une clé (lqa_xxx ou artcb_xxx)
GET  /api/v1/api-keys/list       → liste les clés actives
DELETE /api/v1/api-keys/{key_id} → révoque une clé
GET  /api/v1/api-keys/me         → info clé courante (scopes, quotas)
Middleware: Authorization: Bearer <artcb_key> sur toutes les routes
```

**Cas d'usage :**
- Utilisateur crée une clé → la colle dans son GPT Custom ou LangChain
- Application externe appelle `POST /api/v1/mining/pipeline` avec son token
- La chaîne ARTCB enregistre l'acteur (wallet lié à la clé)

---

## 6. TEST EN ÉCHEC — test_pool_manager_explore_batch

### Détail
```
FAILED tests/test_optimizations_advanced.py::test_pool_manager_explore_batch
assert all(isinstance(g, IRGraph) for g in graphs)
```

**Cause :** `AgentPoolManager.explore_batch()` retourne des résultats qui ne sont pas tous des `IRGraph` — probablement des `None` ou des exceptions silencieuses dans les workers.

**Impact :** 1/234 tests échoue. Chaîne principale non affectée.

**Action requise :** Corriger le test ou la méthode `explore_batch`.

---

## 7. NOUVELLES FONCTIONNALITÉS AJOUTÉES (NON PLANIFIÉES)

### Depuis rapport 067 (dernier audit)

| Fonctionnalité | Fichiers | Commit |
|----------------|---------|--------|
| Provider `cursor` dans ConnectorProvider | `manager.py`, `llm_router.py` | `dac9b19` |
| Provider `watsonx` dans ConnectorProvider | `manager.py`, `llm_router.py`, `sources.py` | `be9da6c` |
| `_cursor_chat()` → `/v1/messages` + `/v1/chat/completions` | `llm_router.py` | `dac9b19` |
| `_watsonx_chat()` → IAM exchange + ML inference | `llm_router.py` | `be9da6c` |
| Replay QA Run #2 — 13 bugs WCAG/UX corrigés | 8 fichiers frontend | `4c720b6` |
| Layout shift demo_live `height:1.5em` | `Home.tsx` | `1352879` |
| Wallet 409 message explicite | `Wallets.tsx` | `1352879` |
| Ngrok nouveau compte `sepermicro2026355` | `.env` | Session |
| Slashing events purge + anti-Sybil reset | `data/slashing_events.jsonl` | Session |

---

## 8. CHECKLIST COMPLÈTE — ÉTAT 2026-07-27

### Backend

| Item | État |
|------|------|
| FastAPI + tous routes | ✅ 93 endpoints |
| Blockchain C natif ML-DSA-65 | ✅ 34 blocs valides |
| Wallet Ed25519 + AES-256-GCM | ✅ 4 wallets |
| Mining pipeline PoL | ✅ |
| Connecteurs LLM (OpenAI, Anthropic, Bob, OpenRouter, Ollama, Cursor, WatsonX) | ✅ enregistrés (test partiel) |
| Connecteurs data source (GitHub, DB, local, PDF) | ✅ GitHub testé OK |
| P2P ML-KEM-768 | ✅ |
| Gouvernance vote | ✅ |
| Groupes + join-request | ✅ |
| Anti-Sybil + Slashing | ✅ |
| Symbols sync | ✅ |
| Pool E2E distribué | ✅ |
| Notifications Telegram | ✅ |
| Multimodal 50+ formats | ✅ |
| **Module API Keys public** | ❌ **Manquant** |
| WatsonX project_id configuré | ❌ Manquant |

### Frontend

| Item | État |
|------|------|
| 14 pages React fonctionnelles | ✅ |
| HashRouter navigation | ✅ |
| Design terminal MC rétro | ✅ |
| WCAG contraste × 4 corrections | ✅ |
| Replay QA 0 bugs open | ✅ |
| **i18n traductions 14 pages** | ❌ **0 % pages** |
| **LanguageSelector fonctionnel end-to-end** | ❌ **Brisé** |
| Wikipedia connector | ❌ Prévu non implémenté |

### Tests

| Suite | Résultat |
|-------|---------|
| `pytest tests/` | 233/234 ✅ (1 échec pool batch) |
| Frontend build TypeScript | ✅ |
| Replay QA exploration | ✅ 24 journeys, 0 bugs |
| `LISTE_TESTS_ARTCB.md` | ⚠️ 210 listés vs 234 réels |

---

## 9. PROCHAINES ACTIONS PRIORITAIRES

### P0 — Critique (bloquant utilisateur)

| # | Action | Fichiers | Effort |
|---|--------|---------|--------|
| 1 | **i18n : ajouter `useTranslation()` dans les 14 pages** | 14 pages `.tsx` | 2–3h |
| 2 | **i18n : compléter 238 clés pour FR/EN/ZH/ES/PT/IT/RU** | `translations.ts` | 3–4h |
| 3 | **Module API Keys public** (`/api-keys/*` + middleware Bearer) | Nouveau `api_keys_routes.py` | 2–3h |
| 4 | **Corriger test_pool_manager_explore_batch** | `test_optimizations_advanced.py` | 30min |

### P1 — Important

| # | Action | Effort |
|---|--------|--------|
| 5 | WatsonX : créer projet ou utiliser `space_id` | 1h |
| 6 | Wikipedia connector (data source) | 1–2h |
| 7 | Mettre à jour `AUTO_PROMPT_ARTCB` + `ROADMAP_GENERAL_ARTCB` | 30min |
| 8 | Synchroniser `LISTE_TESTS_ARTCB.md` (234 tests réels) | 30min |

### P2 — Améliorations

| # | Action |
|---|--------|
| 9 | Cursor LLM : explorer gRPC/WS pour inférence réelle |
| 10 | libp2p natif (remplacer HTTP gossip) |

---

## 10. CONCLUSION

**Avancement global : 72 %**

Le système ARTCB est **fonctionnel et en ligne** (`https://prowler-pantry-stopped.ngrok-free.dev`), la blockchain valide avec 34 blocs ML-DSA-65, Replay QA passe avec 0 bugs open.

Les deux lacunes majeures sont :
1. **i18n brisé** — le sélecteur de langue ne fait rien car aucune page n'appelle `t()`. C'est un bug de régression depuis rapport 060 (travail incomplet).
2. **Module API Keys** — fonctionnalité entièrement absente, nécessaire pour l'intégration ChatGPT/tierce partie.

Ces deux points doivent être traités en priorité absolue.

---
**Rapport généré le :** 2026-07-27  
**Prochaine étape :** Implémenter les points P0 dans l'ordre (i18n → API Keys → test batch)
