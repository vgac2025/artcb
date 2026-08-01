# ARTCB — Guide Confidentialité Homomorphe (Privacy Guide)

## Principe

Le module homomorphe d'ARTCB permet à chaque participant de contribuer à l'apprentissage et au minage partagés **SANS jamais révéler ses données privées**.

```
Tes données (privées)
    ↓ chiffrées sur ta machine (TenSEAL CKKS)
    ↓ envoyées au pool ARTCB (impossible à déchiffrer sans ta clé)
    ↓ agrégées avec les autres contributions (addition homomorphique)
    ↓ résultat agrégé gravé dans ARTCB
    ↓ toi seul peux déchiffrer ta part avec ta clé secrète
```

Le serveur ARTCB ne voit jamais les données brutes, seulement des ciphertexts.

---

## Activation

```bash
# Dans .env
ARTCB_HOMOMORPHIC_MODE=true   # chiffrement actif
ARTCB_HOMOMORPHIC_MODE=false  # mode classique (défaut)
```

Vérifier l'état :
```bash
curl http://localhost:8000/api/v1/privacy/status
```

---

## Installation de TenSEAL (chiffrement CKKS réel)

```bash
pip install tenseal
```

Sans TenSEAL, ARTCB fonctionne en **mode simulé** (XOR + bruit) — suffisant pour les tests, mais non sécurisé pour la production.

---

## Usage Python — côté participant

```python
from src.artcb.privacy import HomomorphicProcessor

# 1. Créer un processeur avec paire de clés
proc = HomomorphicProcessor.create(participant_id="alice")

# 2. Chiffrer tes données (vecteur IR PoL)
mon_vecteur_ir = [0.12, 0.87, 0.45, 0.33, 0.91]  # issu d'un encode ARTCB
cipher = proc.encrypt(mon_vecteur_ir)

print(cipher.to_dict())
# { cipher_hex: "a1b2c3...", vector_size: 5, participant_id: "alice", mode: "ckks" }

# 3. Envoyer cipher au pool ARTCB (le serveur ne peut pas le lire)
# POST /api/v1/privacy/aggregate  { "ciphers": [cipher.to_dict(), ...] }

# 4. Récupérer le résultat agrégé et le déchiffrer
# aggregated = HECipherVector.from_dict(response["aggregated_cipher"])
# result = proc.decrypt(aggregated)
```

---

## Usage via API REST

```bash
# Vérifier le statut
curl http://localhost:8000/api/v1/privacy/status

# Chiffrer un vecteur (idéalement côté client)
curl -X POST http://localhost:8000/api/v1/privacy/encrypt \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.12, 0.87, 0.45], "participant_id": "alice"}'

# Agréger plusieurs vecteurs chiffrés côté serveur
curl -X POST http://localhost:8000/api/v1/privacy/aggregate \
  -H "Content-Type: application/json" \
  -d '{
    "ciphers": [
      {"cipher_hex": "...", "vector_size": 3, "participant_id": "alice", "mode": "simulated"},
      {"cipher_hex": "...", "vector_size": 3, "participant_id": "bob",   "mode": "simulated"}
    ]
  }'
```

---

## Usage FederatedAggregator (côté pool ARTCB)

```python
from src.artcb.privacy import FederatedAggregator, HomomorphicProcessor

# Participants envoient leurs contributions chiffrées
proc_alice = HomomorphicProcessor.create(participant_id="alice")
proc_bob   = HomomorphicProcessor.create(participant_id="bob")

cipher_alice = proc_alice.encrypt([0.12, 0.87, 0.45])
cipher_bob   = proc_bob.encrypt([0.33, 0.65, 0.78])

# Côté pool ARTCB — aucun déchiffrement individuel
agg = FederatedAggregator()
agg.add_contribution("alice", cipher_alice, pol_score=0.87)
agg.add_contribution("bob",   cipher_bob,   pol_score=0.72)

round_result = agg.finalize()
print(round_result.summary())
# {
#   "round_id": "a1b2c3d4e5f6",
#   "participant_count": 2,
#   "aggregated_pol_score": 0.795,
#   "homomorphic": True,
#   "has_aggregated_result": True
# }

# Le résultat agrégé chiffré est gravé dans ARTCB
# Les participants déchiffrent avec leur propre clé
```

---

## Schéma CKKS — paramètres

| Paramètre | Valeur | Rôle |
|-----------|--------|------|
| `poly_modulus_degree` | 8192 | Sécurité 128 bits |
| `coeff_mod_bit_sizes` | [60, 40, 40, 60] | Précision des calculs |
| `scale` | 2^40 | Précision flottant |
| Schéma | CKKS | Adapté aux vecteurs de flottants |

---

## Garanties de confidentialité

| Scenario | Données visibles par le serveur |
|----------|--------------------------------|
| Mode classique (`HOMOMORPHIC_MODE=false`) | ✅ Données brutes visibles |
| Mode homomorphe (`HOMOMORPHIC_MODE=true`) | ❌ Uniquement les ciphertexts |
| Agrégation homomorphique | ❌ Le serveur n'a jamais accès aux contributions individuelles |

---

## Limitations actuelles (Phase 14.3)

- L'agrégation CKKS réelle serveur-side nécessite que tous les participants partagent le même contexte public — à implémenter en Phase 14.3 avancée
- TenSEAL supporte uniquement Python 3.8-3.11 sur certaines plateformes — vérifier la compatibilité
- Le mode simulé (sans TenSEAL) n'est PAS sécurisé pour la production

---

*Documentation Phase 14.3 — ARTCB 2026*
