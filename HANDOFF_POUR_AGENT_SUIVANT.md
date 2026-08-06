# HANDOFF — Pour l'agent suivant (état complet main)

**Horodatage :** 2026-08-06T23:45:00Z — **mis à jour rapport 107-108**
**Commit :** `ea56083` — push direct main
**Dépôt :** https://github.com/vgac2025/lvx
**Tests :** 488/488 PASS | 8 skipped bridges live (normaux) | Build TS 0 erreur

---

## Ce que l'utilisateur exige (priorité absolue)

1. **Exécution sur SA machine** — pas sur la VM Cloud Cursor (`hostname=cursor`, `/workspace`).
2. **Pas de frontend / pas de navigateur** pour valider la démo.
3. **PROTOCOLE_ARTCB** : DEBUG, pas de mock, logs lus → rapport .md, avant/après.
4. **Pas de vidéo hackathon** — hors périmètre agent dev.
5. L'utilisateur est frustré : livrer scripts + doc pour qu'il exécute **chez lui**, ou qu'un agent avec accès local le fasse.

---

## État code (~92 % MVP)

| Phase | % | Fichiers clés |
|-------|---|---------------|
| 0 Spec | 100 % | CDC v1.2, TOKENOMICS, RESEAU_DEVNET |
| 1 IR | 100 % | `src/artcb/ir/` — 42 tests |
| 2 Backend | 100 % | `src/api/`, PoL, agents, WS |
| 3 Blockchain C | 85 % | `src/c/libartcb_chain.c`, `chain/manager.py` — manque rewards collectifs, devnet P2P |
| 4 Frontend | 100 % | `frontend/` — **optionnel**, user ne veut pas l'ouvrir |
| Démo API | 100 % | `scripts/demo_live.py`, `run_real_local.sh` |

---

## Scripts à faire exécuter par l'utilisateur sur SON PC

```bash
git clone https://github.com/vgac2025/lvx.git
cd lvx
bash scripts/setup_machine_locale.sh
bash scripts/run_real_local.sh
```

Preuve machine : `logs/machine_fingerprint.txt` → `execution_env=USER_MACHINE`

Guide : **`EXECUTION_MACHINE_UTILISATEUR.md`**  
Secrets : **`ENV_A_REMPLIR_ARTCB`** → `cp ENV_A_REMPLIR_ARTCB .env` puis coller vos clés

---

## Rapports (000 → 012)

| # | Fichier | Sujet |
|---|---------|-------|
| 009 | `009_demo_live_execution.md` | Première démo (incluait GUI — voir 010) |
| 010 | `010_demo_api_sans_frontend.md` | Démo API-only |
| 011 | `011_execution_reelle_locale_20260704.md` | Exécution cloud (erreur « local ») |
| 012 | `012_correction_cloud_vs_machine_utilisateur.md` | Cloud ≠ PC utilisateur |

---

## Décisions actées (DECISIONS_UTILISATEUR_ARTCB)

- D-001 : merge/push `main` systématique
- D-008 : rule-based + Bob LLM (deux chemins)
- D-010 : démo = livre Wailly 100 %
- D-014→D-022 : tokenomics 21M, PoL collectif, pARTCB/pubARTCB, mineurs humain+IA, Bob/Gradium clés

---

## Reste à coder

1. Phase 3 : `contributors[]` rewards collectifs, `artcb-devnet`, faucet
2. Gradium TTS API (UI a fallback Web Speech)
3. Exécution **prouvée** sur machine utilisateur (humain ou agent local)

---

## Commandes dev (cloud ou local)

```bash
make chain && make test
make api                    # :8000
python3 scripts/demo_live.py
make demo-real              # setup + demo si API up
```

---

## Erreurs connues / pièges

- `libssl-dev` requis pour build C (Debian: `apt install libssl-dev`)
- `PYTHONPATH=src` pour imports `artcb.*`
- Rapport 011 = cloud only — ne pas présenter comme exécution utilisateur
- Ne pas imposer `make frontend` à l'utilisateur

---

## Commits récents main

```
9277e8f docs: cloud vs machine utilisateur
e655ca0 feat: run_real_local.sh + rapport 011
51f3e23 fix: démo API-only
16dc7e0 feat: démo live + rapport 009
caadc70 feat: Phase 4 frontend
e3328ec feat: Phase 2+3 backend chain
```
