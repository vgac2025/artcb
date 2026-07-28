"""ARTCB tokenomics constants — single source of truth."""

# 1 ARTCB = 10^8 satoshi (like Bitcoin)
SATOSHI_PER_ARTCB = 100_000_000

# Block reward at genesis (halving every HALVING_INTERVAL blocks)
INITIAL_BLOCK_REWARD_ARTCB = 1.0
INITIAL_BLOCK_REWARD_SATOSHI = int(INITIAL_BLOCK_REWARD_ARTCB * SATOSHI_PER_ARTCB)

HALVING_INTERVAL = 210_000
MAX_HALVINGS = 64

# Supply max réelle (série géométrique convergente) :
# INITIAL * HALVING * 2 = 1.0 * 210_000 * 2 = 420_000 ARTCB
# Note : la documentation historique mentionnait 21M (erreur héritée de Bitcoin
#        où INITIAL=50 BTC donnait 50 × 210000 × 2 = 21 000 000 BTC).
#        Avec INITIAL=1 ARTCB, la supply max réelle est 420 000 ARTCB.
MAX_SUPPLY_ARTCB = 420_000.0
MAX_SUPPLY_SATOSHI = int(MAX_SUPPLY_ARTCB * SATOSHI_PER_ARTCB)
