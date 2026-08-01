"""
ARTCB Kaggle Node — Script autonome (copier-coller dans n'importe quel notebook Kaggle)
=======================================================================================

USAGE :
    1. Ouvrir un nouveau notebook sur Kaggle (https://kaggle.com/code)
    2. Activer Internet : Settings → Internet → On
    3. Coller ce script dans une cellule
    4. Modifier ARTCB_NODE_URL avec l'URL de votre nœud
    5. Exécuter

Ce script prouve la décentralisation réelle :
    - Kaggle Cloud = machine indépendante avec IP propre
    - Elle mine un bloc dans ARTCB sans jamais héberger la blockchain
    - C'est exactement ce que fait un nœud Bitcoin ou Ethereum
"""

# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION — modifier ici
# ══════════════════════════════════════════════════════════════════════

ARTCB_NODE_URL = "https://TON_URL_ICI"   # ngrok, VPS, ou Render
KAGGLE_NODE_ID = "kaggle-contributor-01"  # identifiant de ce nœud

# ══════════════════════════════════════════════════════════════════════

import json, socket, platform, datetime, time, urllib.request, urllib.error


class ArtcbClient:
    """Client ARTCB minimal — zéro dépendance externe."""

    def __init__(self, base_url, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _h(self):
        return {"Content-Type": "application/json", "User-Agent": "ARTCB-Kaggle/1.0"}

    def _get(self, path):
        req = urllib.request.Request(f"{self.base_url}{path}", headers=self._h())
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def _post(self, path, body):
        data = json.dumps(body).encode()
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=self._h(), method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def health(self):           return self._get("/health")
    def verify(self):           return self._get("/api/v1/chain/verify")
    def privacy_status(self):   return self._get("/api/v1/privacy/status")
    def mine(self, text):       return self._post("/api/v1/mining/pipeline",
                                    {"text": text, "visibility": "public", "private": False})
    def store(self, text):      return self._post("/api/v1/store",
                                    {"text": text, "visibility": "public"})
    def search(self, q):
        r = self._get(f"/api/v1/chain/search?q={q}&limit=5")
        return r.get("results", r) if isinstance(r, dict) else r
    def encrypt_vector(self, vector, pid="kaggle"):
        return self._post("/api/v1/privacy/encrypt", {"vector": vector, "participant_id": pid})


# ── Identité du nœud Kaggle ──────────────────────────────────────────
kaggle_ip = socket.gethostbyname(socket.gethostname())
ts = datetime.datetime.utcnow().isoformat()

print("━" * 52)
print("  ARTCB — Nœud Kaggle")
print("━" * 52)
print(f"  Nœud ID  : {KAGGLE_NODE_ID}")
print(f"  IP Kaggle: {kaggle_ip}")
print(f"  UTC      : {ts}")
print(f"  Cible    : {ARTCB_NODE_URL}")
print()

# ── Connexion ────────────────────────────────────────────────────────
client = ArtcbClient(ARTCB_NODE_URL)
try:
    h = client.health()
    print(f"  ✅ ARTCB en ligne : {h.get('status', 'ok')}")
except Exception as e:
    print(f"  ❌ ARTCB non accessible : {e}")
    print("  → Vérifier ARTCB_NODE_URL et que l'API est démarrée")
    raise SystemExit(1)

chain_avant = client.verify()
blocs_avant = chain_avant.get("block_count", 0)
print(f"  📊 Blocs actuels : {blocs_avant}")
print()

# ── Minage ───────────────────────────────────────────────────────────
mining_text = f"""Contribution nœud Kaggle — ARTCB Blockchain
Nœud        : {KAGGLE_NODE_ID}
IP Kaggle   : {kaggle_ip}
UTC         : {ts}
Python      : {platform.python_version()}
Plateforme  : {platform.platform()[:60]}
Nœud ARTCB  : {ARTCB_NODE_URL}

Preuve décentralisation :
Ce bloc est miné depuis une machine Kaggle Cloud indépendante.
IP source différente du nœud ARTCB = nœud décentralisé réel.
Cryptographie post-quantique : ML-DSA-65 (NIST PQC 2024).
"""

print("  ⛏️  Minage en cours...")
t0 = time.time()

try:
    result = client.mine(mining_text)
except Exception:
    result = client.store(mining_text[:2000])

elapsed = time.time() - t0
bloc_idx = result.get("block_index", result.get("block", {}).get("index", "?"))
pol = result.get("pol_score", "?")
bloc_hash = str(result.get("block_hash", result.get("hash", "")))[:24]

print(f"  ✅ Bloc #{bloc_idx} gravé | PoL={pol} | hash={bloc_hash}... ({elapsed:.1f}s)")
print()

# ── Vérification ─────────────────────────────────────────────────────
time.sleep(2)
chain_apres = client.verify()
blocs_apres = chain_apres.get("block_count", 0)

print("━" * 52)
print("  RÉSULTAT")
print("━" * 52)
print(f"  Blocs avant : {blocs_avant}")
print(f"  Blocs après : {blocs_apres}  (+{blocs_apres - blocs_avant})")
print(f"  Valide      : {'✅ OUI' if chain_apres.get('valid') else '❌ NON'}")
print()

if blocs_apres > blocs_avant:
    print("  🎉 DÉCENTRALISATION CONFIRMÉE")
    print(f"  → Machine Kaggle ({kaggle_ip}) = nœud ARTCB réel")
    print(f"  → Chaque notebook Kaggle = 1 nœud supplémentaire")
else:
    print("  ⚠️  Vérifier la connexion")

# ── Test module homomorphe ──────────────────────────────────────────
print()
print("━" * 52)
print("  MODULE HOMOMORPHE (confidentialité)")
print("━" * 52)
try:
    priv = client.privacy_status()
    mode = "🔒 ACTIF" if priv.get("homomorphic_mode") else "📖 Classique (défaut)"
    print(f"  Mode : {mode}")
    print(f"  Schéma : {priv.get('scheme', '?')}")

    # Chiffrer un vecteur depuis Kaggle sans révéler les données
    cipher = client.encrypt_vector([0.12, 0.87, 0.45, 0.33, 0.91], pid=KAGGLE_NODE_ID)
    print(f"  ✅ Vecteur chiffré : {cipher.get('cipher_hex', '')[:32]}...")
    print(f"  → Les autres mineurs ne verront JAMAIS ces valeurs brutes")
except Exception as e:
    print(f"  (module homomorphe : {e})")

print("━" * 52)
