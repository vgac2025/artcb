"""ARTCB tokenomics constants — single source of truth.

Decisions validees (D-014 revise) :
  - Supply max      : 21 000 000 ARTCB (hard cap immuable)
  - Reward initial  : 1 ARTCB/bloc
  - Halving fixe    : tous les 105 000 blocs (reduit de moitie vs Bitcoin)
  - Halving dyna.   : s'accelere proportionnellement si vitesse > VELOCITY_REFERENCE
  - Anti-Sybil      : conserve pour securite anti-malveillants uniquement
  - Pas de rate-limit : l'IA fonctionne en temps reel sans file d'attente

Contexte (source : TechCrunch/Gartner juin 2026) :
  - 3,4 milliards d'utilisateurs IA mondiaux en 2026
  - ARTCB vise la totalite des plateformes IA (ChatGPT, Gemini, Claude, Meta AI)
  - A 0.1% adoption = 3.4M users -> supply epuisee en 2 jours sans halving dynamique
  - Le halving dynamique corrige cela automatiquement SANS bloquer le minage temps reel

CONSTANTES IMMUABLES (rapports 112 + 106 — 2026-08-04) :
  Ces valeurs NE PEUVENT PAS etre modifiees via .env / Doppler / Replit secrets.
  Elles sont utilisees directement par le code (IMMUTABLE_*).
  Tout changement necessite un vote de gouvernance + nouveau deploiement de code.
  Doppler et .env sont reserves a l'usage personnel du fondateur et phase de dev.
  Ils ne contiennent JAMAIS de parametres affectant le protocole en production.

  IMMUTABLE_CREATOR_VOTE_WEIGHT_MULTIPLIER :
    Poids createur = MULTIPLIER x nombre de votes communaute emis.
    Ratio constant = 20/21 = 95.24% quel que soit le nombre d'utilisateurs.
    Jamais depuis .env — grave dans le genesis block.
    Modifier cette valeur sans vote = violation du protocole ARTCB.
"""

# ── Unité monétaire ────────────────────────────────────────────────────────
# 1 ARTCB = 10^8 satoshi (meme granularite que Bitcoin)
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
# 21 000 000 ARTCB — decision de design immuable (D-014).
# Le reseau rejette tout bloc qui ferait depasser ce plafond.
MAX_SUPPLY_ARTCB    = 21_000_000.0
MAX_SUPPLY_SATOSHI  = int(MAX_SUPPLY_ARTCB * SATOSHI_PER_ARTCB)

# ── CONSTANTES IMMUABLES DU PROTOCOLE ─────────────────────────────────────
# Ces valeurs sont utilisees DIRECTEMENT dans le code — jamais depuis .env.
# Elles refletent les regles gravees dans le genesis block (protocol_constants).
# Modifier ces valeurs sans vote de gouvernance = violation du protocole ARTCB.
#
# IMMUTABLE_POL_THRESHOLD   : seuil minimum de qualite PoL — aucun bloc en dessous
#                             de ce score n'est jamais accepte dans la chaine.
#                             Correspond a genesis["protocol_constants"]["pol_threshold"].
#
# IMMUTABLE_MAX_SUPPLY_ARTCB : plafond absolu de la supply — identique a MAX_SUPPLY_ARTCB
#                              mais nomme IMMUTABLE pour signaler l'interdiction de le
#                              lire depuis une variable d'environnement.
#
# IMMUTABLE_SATOSHI_PER_ARTCB : granularite monetaire — 1 ARTCB = 10^8 satoshi.
#                               Immuable pour garantir la coherence des calculs
#                               sur toute la duree de vie de la chaine.
IMMUTABLE_POL_THRESHOLD    = 0.6           # Jamais depuis .env — gravé genesis
IMMUTABLE_MAX_SUPPLY_ARTCB = 21_000_000    # Jamais depuis .env — gravé genesis
IMMUTABLE_SATOSHI_PER_ARTCB = 100_000_000  # Jamais depuis .env — granularite fixe

# ── Multiplicateur de poids du vote createur ───────────────────────────────
# Poids createur = max(1, votes_communaute * IMMUTABLE_CREATOR_VOTE_WEIGHT_MULTIPLIER)
# Ratio constant : 20 / 21 = 95.24% quelle que soit la taille de la communaute.
# Jamais depuis .env — immuable par definition du protocole.
# Utilise par governance/manager.py — ne jamais lire depuis une variable d'environnement.
IMMUTABLE_CREATOR_VOTE_WEIGHT_MULTIPLIER = 20

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

