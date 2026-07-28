"""ARTCB tokenomics constants — single source of truth."""

# 1 ARTCB = 10^8 satoshi (like Bitcoin)
SATOSHI_PER_ARTCB = 100_000_000

# Block reward at genesis (halving every HALVING_INTERVAL blocks)
INITIAL_BLOCK_REWARD_ARTCB = 1.0
INITIAL_BLOCK_REWARD_SATOSHI = int(INITIAL_BLOCK_REWARD_ARTCB * SATOSHI_PER_ARTCB)

# Halving identique à Bitcoin (tous les 210 000 blocs)
# Mais : ARTCB est une blockchain IA à croissance explosive — la vitesse de bloc
# augmentera proportionnellement au nombre d'utilisateurs IA (plateformes, agents).
# Avec des millions d'utilisateurs IA, les 21M ARTCB peuvent être épuisés en années,
# pas en siècles. C'est un choix de design voulu : la rareté s'intensifie avec l'adoption.
HALVING_INTERVAL = 210_000
MAX_HALVINGS = 64

# Supply max : 21 000 000 ARTCB (décision de design — D-014)
# Formule : SUPPLY = INITIAL_REWARD * HALVING_INTERVAL * 2 * N_ADJUSTMENTS
# Avec INITIAL=1 et HALVING=210_000 : la série converge vers 420_000 ARTCB mathématiquement,
# MAIS la supply cap de 21M est une contrainte HARD CAP indépendante,
# imposée par le protocole (validation blockchain refuse tout bloc qui dépasserait 21M).
# Les halvings réduisent le reward avant d'atteindre ce plafond si la vitesse accélère.
# → À forte adoption IA (millions d'utilisateurs), la supply sera consommée bien avant
#   l'épuisement mathématique de la série géométrique.
MAX_SUPPLY_ARTCB = 21_000_000.0
MAX_SUPPLY_SATOSHI = int(MAX_SUPPLY_ARTCB * SATOSHI_PER_ARTCB)

# Made with Bob
