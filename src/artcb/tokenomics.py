"""ARTCB tokenomics constants — single source of truth.

Décisions validées (D-014 révisé — rapport 079b/080) :
  - Supply max      : 21 000 000 ARTCB (hard cap immuable)
  - Reward initial  : 1 ARTCB/bloc
  - Halving fixe    : tous les 105 000 blocs (réduit de moitié vs Bitcoin)
  - Halving dyna.   : s'accélère proportionnellement si vitesse > VELOCITY_REFERENCE
  - Anti-Sybil      : conservé pour sécurité anti-malveillants uniquement
  - Pas de rate-limit : l'IA fonctionne en temps réel sans file d'attente

Contexte (source : TechCrunch/Gartner juin 2026) :
  - 3,4 milliards d'utilisateurs IA mondiaux en 2026
  - ARTCB vise la totalité des plateformes IA (ChatGPT, Gemini, Claude, Meta AI…)
  - À 0.1% adoption = 3.4M users → supply épuisée en 2 jours sans halving dynamique
  - Le halving dynamique corrige cela automatiquement SANS bloquer le minage temps réel
"""

# ── Unité monétaire ────────────────────────────────────────────────────────
# 1 ARTCB = 10^8 satoshi (même granularité que Bitcoin)
SATOSHI_PER_ARTCB = 100_000_000

# ── Reward initial ─────────────────────────────────────────────────────────
INITIAL_BLOCK_REWARD_ARTCB    = 1.0
INITIAL_BLOCK_REWARD_SATOSHI  = int(INITIAL_BLOCK_REWARD_ARTCB * SATOSHI_PER_ARTCB)

# ── Halving fixe de base ───────────────────────────────────────────────────
# 105 000 blocs (moitié de l'intervalle Bitcoin de 210 000).
# Raison : à faible adoption, les halvings arrivent plus tôt → émission plus
# contrôlée dès le départ, même en devnet solo.
HALVING_INTERVAL = 105_000

# Nombre maximal de halvings (après quoi reward = 0)
MAX_HALVINGS = 64

# ── Supply max (hard cap absolue) ─────────────────────────────────────────
# 21 000 000 ARTCB — décision de design immuable (D-014).
# Le réseau rejette tout bloc qui ferait dépasser ce plafond.
MAX_SUPPLY_ARTCB    = 21_000_000.0
MAX_SUPPLY_SATOSHI  = int(MAX_SUPPLY_ARTCB * SATOSHI_PER_ARTCB)

# ── Halving dynamique ──────────────────────────────────────────────────────
# Si la vitesse de minage dépasse VELOCITY_REFERENCE blocs/jour, le reward
# est divisé proportionnellement par un facteur dynamique.
#
# Formule complète du reward pour un bloc à l'index I :
#
#   epoch_fixe    = I // HALVING_INTERVAL
#   epoch_dyn     = floor(log2(max(1, velocity_24h / VELOCITY_REFERENCE)))
#   epoch_total   = epoch_fixe + epoch_dyn
#   reward        = INITIAL_REWARD >> min(epoch_total, MAX_HALVINGS - 1)
#
# Exemple :
#   velocity = 1 440 blocs/jour (= VELOCITY_REFERENCE × 10)
#   → epoch_dyn = floor(log2(10)) = 3
#   → 3 halvings dynamiques supplémentaires → reward divisé par 8
#   → un bloc à l'index 0 vaut 1/8 ARTCB au lieu de 1 ARTCB
#
# Effets :
#   - 1 utilisateur (22 blocs/j)     → epoch_dyn = 0 (pas de pénalité)
#   - 10K utilisateurs (10K blocs/j) → epoch_dyn = 6 → reward/64
#   - 1M utilisateurs (1M blocs/j)   → epoch_dyn = 13 → reward/8192
#   - 1B utilisateurs (1B blocs/j)   → epoch_dyn = 26 → reward/67M
#
# Résultat : la supply dure toujours ~21M ARTCB quelle que soit la vitesse,
# sans jamais bloquer un seul utilisateur (pas de file d'attente).
#
VELOCITY_REFERENCE = 144  # blocs/jour — référence Bitcoin (ajustable par gouvernance)

# Fenêtre temporelle pour mesurer la vitesse actuelle (en secondes)
VELOCITY_WINDOW_SECONDS = 86_400  # 24 heures

# Made with Bob
