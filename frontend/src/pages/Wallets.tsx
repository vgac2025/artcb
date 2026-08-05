import { useEffect, useState } from "react";
import {
  createWallet,
  fetchFoundersAllocation,
  fetchWalletBalance,
  fetchWalletRewards,
  fetchWallets,
} from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { useTranslation } from "../i18n/useTranslation";

type CreatedWallet = {
  name: string;
  address: string;
  address_v2?: string;
  public_key_hex: string;
  hybrid: boolean;
};

export function Wallets() {
  const { t } = useTranslation();
  const { actorAddress, setActorAddress } = useDashboard();
  const [wallets, setWallets] = useState<
    Array<{ address: string; name: string; balance?: number; rewards?: number }>
  >([]);
  const [founders, setFounders] = useState<
    Array<{ founder_id: number; name: string; balance_artcb: number; is_creator?: boolean }>
  >([]);
  const [newName, setNewName] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [rewardHistory, setRewardHistory] = useState<
    Array<{ block_index: number; reward_artcb: number; pol_score: number; timestamp: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // ── Wallet créé — affiché à l'utilisateur ─────────────────────────
  const [createdWallet, setCreatedWallet] = useState<CreatedWallet | null>(null);
  const [copied, setCopied] = useState(false);
  // UX-1: copier depuis la grille (quel wallet est en cours de copie)
  const [copiedGrid, setCopiedGrid] = useState<string | null>(null);

  // ── Import wallet (entrer une adresse existante) ──────────────────
  const [importAddress, setImportAddress] = useState("");
  const [importError, setImportError]     = useState<string | null>(null);

  const reload = async () => {
    const list = await fetchWallets();
    const withBal = await Promise.all(
      list.map(async (w) => {
        try {
          const b = await fetchWalletBalance(w.address);
          const r = await fetchWalletRewards(w.address);
          return { ...w, balance: b.balance_artcb, rewards: r.total_artcb };
        } catch {
          return { ...w, balance: 0, rewards: 0 };
        }
      }),
    );
    setWallets(withBal);
  };

  useEffect(() => {
    reload().catch(() => setWallets([]));
    fetchFoundersAllocation()
      .then((f) => setFounders(f.balances ?? []))
      .catch(() => {});
  }, []);

  // ── Créer un nouveau wallet ────────────────────────────────────────
  const handleCreate = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    setError(null);
    setCreatedWallet(null);
    try {
      const w = await createWallet(newName.trim());
      setActorAddress(w.address);
      setCreatedWallet(w);         // <── Affichage immédiat à l'utilisateur
      setNewName("");
      await reload();
    } catch (err: unknown) {
      const axErr = err as { response?: { data?: { detail?: string }; status?: number } };
      if (axErr?.response?.status === 409) {
        setError(`Wallet "${newName.trim()}" existe déjà — choisissez un autre nom.`);
      } else {
        setError(axErr?.response?.data?.detail ?? (err instanceof Error ? err.message : String(err)));
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Copier une adresse ─────────────────────────────────────────────
  const copyAddress = (addr: string) => {
    navigator.clipboard?.writeText(addr).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      // Fallback — sélectionner le texte
      const el = document.createElement("textarea");
      el.value = addr;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // UX-1 FIX: copier une adresse depuis la grille
  const copyFromGrid = (addr: string) => {
    navigator.clipboard?.writeText(addr).then(() => {
      setCopiedGrid(addr);
      setTimeout(() => setCopiedGrid(null), 2000);
    }).catch(() => {
      const el = document.createElement("textarea");
      el.value = addr;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopiedGrid(addr);
      setTimeout(() => setCopiedGrid(null), 2000);
    });
  };

  // UX-3 FIX: déconnexion — vider actorAddress
  const handleDisconnect = () => {
    setActorAddress("");
  };

  // ── Importer un wallet existant ────────────────────────────────────
  const handleImport = async () => {
    const addr = importAddress.trim();
    if (!addr) return;
    setImportError(null);
    try {
      const b = await fetchWalletBalance(addr);
      setActorAddress(addr);
      setImportError(null);
      setImportAddress("");
      // Ajouter à la liste locale si pas déjà présent
      if (!wallets.find((w) => w.address === addr)) {
        setWallets((prev) => [
          ...prev,
          { address: addr, name: `Import (${addr.slice(0, 8)}…)`, balance: b.balance_artcb, rewards: 0 },
        ]);
      }
    } catch {
      setImportError("Adresse introuvable sur la blockchain — vérifiez l'adresse.");
    }
  };

  const showRewards = async (address: string) => {
    setSelected(address);
    const r = await fetchWalletRewards(address);
    setRewardHistory(r.rewards);
  };

  const slots = Array.from({ length: 27 }, (_, i) => wallets[i] ?? null);

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('wallets_title')}</h1>

      {/* UX-4 FIX: Wallet actif affiché en haut — avec bouton déconnexion */}
      {actorAddress ? (
        <div className="panel" style={{ borderColor: "var(--mc-grass, #56c426)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <span style={{ color: "var(--mc-grass, #56c426)", fontWeight: 700, marginRight: 8 }}>◇ Wallet actif :</span>
            <span className="mc-mono" style={{ fontSize: 13 }}>{actorAddress}</span>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button onClick={() => copyAddress(actorAddress)}>
              {copied ? "[OK] Copié !" : "Copier"}
            </button>
            {/* UX-3 FIX: Bouton déconnexion */}
            <button onClick={handleDisconnect} style={{ color: "var(--mc-redstone, #c0392b)", borderColor: "var(--mc-redstone, #c0392b)" }}>
              ✕ Se déconnecter
            </button>
          </div>
        </div>
      ) : (
        /* UX-2 FIX: Bandeau onboarding si aucun wallet actif */
        <div className="panel" style={{ borderColor: "var(--mc-gold, #ffd700)", background: "rgba(255,215,0,0.05)" }}>
          <p style={{ margin: 0, color: "var(--mc-gold, #ffd700)", fontWeight: 700 }}>
            ◇ Pas encore de wallet actif — créez-en un ci-dessous ou connectez-vous avec votre adresse existante.
          </p>
        </div>
      )}

      {/* ── Panneau : Créer un wallet ─────────────────────────── */}
      <div className="panel">
        <h2>{t('wallets_create_title')}</h2>
        <div className="toolbar">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t('wallets_create_placeholder')}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button className="primary" onClick={handleCreate} disabled={loading || !newName.trim()}>
            {loading ? "Création…" : t('wallets_create_button')}
          </button>
        </div>
        {error && <p className="mc-error">{error}</p>}
      </div>

      {/* ── Résultat création : adresse affichée à l'utilisateur ─ */}
      {createdWallet && (
        <div className="panel" style={{ border: "2px solid var(--mc-grass, #56c426)" }}>
          <h2 style={{ color: "var(--mc-grass, #56c426)" }}>[OK] Wallet créé — conservez votre adresse !</h2>
          <p style={{ fontSize: 13, marginBottom: 8, color: "var(--terminal-muted, #8b949e)" }}>
            <strong>Important :</strong> Cette adresse est votre identité sur la blockchain ARTCB.
            Copiez-la maintenant — elle ne sera plus affichée en clair après fermeture.
          </p>

          <table className="mc-table" style={{ marginBottom: 12 }}>
            <tbody>
              <tr>
                <td style={{ fontWeight: 700, width: 120 }}>Nom</td>
                <td className="mc-mono">{createdWallet.name}</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 700 }}>Adresse</td>
                <td>
                  <span className="mc-mono mc-gold-text" style={{ wordBreak: "break-all", fontSize: 12 }}>
                    {createdWallet.address}
                  </span>
                </td>
              </tr>
              {createdWallet.address_v2 && (
                <tr>
                  <td style={{ fontWeight: 700 }}>Adresse v2 (PQC)</td>
                  <td>
                    <span className="mc-mono" style={{ wordBreak: "break-all", fontSize: 12, color: "var(--mc-sky, #5bc0de)" }}>
                      {createdWallet.address_v2}
                    </span>
                  </td>
                </tr>
              )}
              <tr>
                <td style={{ fontWeight: 700 }}>Type</td>
                <td className="mc-mono">
                  {createdWallet.hybrid ? "Ed25519 + ML-DSA-65 (post-quantique)" : "Ed25519 standard"}
                </td>
              </tr>
            </tbody>
          </table>

          <div className="toolbar">
            <button className="primary" onClick={() => copyAddress(createdWallet.address)}>
              {copied ? "[OK] Copié !" : "Copier l'adresse"}
            </button>
            {createdWallet.address_v2 && (
              <button onClick={() => copyAddress(createdWallet.address_v2!)}>
                Copier adresse v2 (PQC)
              </button>
            )}
            <button onClick={() => setCreatedWallet(null)} style={{ marginLeft: "auto" }}>
              Fermer
            </button>
          </div>
        </div>
      )}

      {/* ── Panneau : Importer un wallet existant ─────────────── */}
      <div className="panel">
        <h2>Connexion — J'ai déjà un wallet</h2>
        <p style={{ fontSize: 13, color: "var(--terminal-muted, #8b949e)", marginBottom: 8 }}>
          Entrez votre adresse ARTCB pour accéder à votre compte et consulter votre solde.
        </p>
        <div className="toolbar">
          <input
            value={importAddress}
            onChange={(e) => setImportAddress(e.target.value)}
            placeholder="artcb1… ou adresse Base64 de votre wallet"
            style={{ fontFamily: "monospace", fontSize: 13 }}
            onKeyDown={(e) => e.key === "Enter" && handleImport()}
          />
          <button onClick={handleImport} disabled={!importAddress.trim()}>
            Se connecter
          </button>
        </div>
        {importError && <p className="mc-error">{importError}</p>}
      </div>

      {/* ── Grille wallets (coffre) ────────────────────────────── */}
      <div className="panel mc-chest">
        <h2 style={{ marginBottom: "0.75rem" }}>
          Vos wallets ({wallets.length})
          {wallets.length === 0 && <span className="mc-muted" style={{ fontSize: 13, fontWeight: 400, marginLeft: 8 }}>— Créez votre premier wallet ci-dessus ↑</span>}
        </h2>
        {/* UX-2 FIX: message explicite quand aucun wallet */}
        {wallets.length === 0 && (
          <div style={{ textAlign: "center", padding: "2rem 1rem", color: "var(--muted)" }}>
            <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>◇</div>
            <p>Vous n'avez pas encore de wallet.</p>
            <p style={{ fontSize: 13 }}>Un wallet est votre identité sur la blockchain ARTCB — il vous permet de signer des blocs et de recevoir des récompenses ARTCB.</p>
          </div>
        )}
        <div className="mc-chest-grid">
          {slots.map((w, i) => (
            <div
              key={i}
              className={`mc-chest-slot${w ? " mc-chest-filled" : ""}${w && w.address === actorAddress ? " mc-chest-active" : ""}`}
              onClick={() => w && showRewards(w.address)}
              onKeyDown={(e) => e.key === "Enter" && w && showRewards(w.address)}
              role={w ? "button" : undefined}
              tabIndex={w ? 0 : undefined}
              title={w ? `${w.name} — ${w.address}` : undefined}
            >
              {w ? (
                <>
                  {w.address === actorAddress && <div style={{ fontSize: 8, color: "var(--mc-grass)", textAlign: "center" }}>● ACTIF</div>}
                  <div className="mc-chest-icon">◇</div>
                  <div className="mc-chest-name">{w.name}</div>
                  <div className="mc-gold-text">{(w.balance ?? 0).toFixed(2)} ₳</div>
                  <div className="mc-mono mc-chest-addr">{w.address.slice(0, 8)}…</div>
                  {/* UX-1 FIX: bouton copier + bouton activer sur chaque wallet */}
                  <div style={{ display: "flex", gap: 2, marginTop: 4, justifyContent: "center" }} onClick={(e) => e.stopPropagation()}>
                    <button
                      style={{ fontSize: 9, padding: "1px 4px" }}
                      onClick={() => copyFromGrid(w.address)}
                      title="Copier l'adresse"
                    >
                      {copiedGrid === w.address ? "✓" : "⧉"}
                    </button>
                    {w.address !== actorAddress && (
                      <button
                        style={{ fontSize: 9, padding: "1px 4px", color: "var(--mc-grass)" }}
                        onClick={() => setActorAddress(w.address)}
                        title="Activer ce wallet"
                      >
                        ▶
                      </button>
                    )}
                  </div>
                </>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {/* ── Founders (v2 : Créateur + Dev) ───────────────────── */}
      {founders.length > 0 && (
        <div className="panel">
          <h2>{t('wallets_founders_title')}</h2>
          <div className="mc-hotbar">
            {founders.map((f) => (
              <div
                key={f.founder_id}
                className={`mc-slot ${f.is_creator ? "mc-slot-gold" : "mc-slot-active"}`}
                title={f.is_creator ? "Compte Créateur — droits absolus (vote weight 999 999)" : "Compte Développement"}
              >
                <div className="mc-kpi-label">
                  {f.name}
                  {f.is_creator && <span style={{ marginLeft: 4, fontSize: 10 }}>[CREATEUR]</span>}
                </div>
                <div className="mc-kpi-value">{f.balance_artcb.toLocaleString()} ₳</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Historique rewards ─────────────────────────────────── */}
      {selected && (
        <div className="panel">
          <h2>{t('wallets_rewards_title')} — {selected.slice(0, 16)}…</h2>
          <table className="mc-table">
            <thead>
              <tr>
                <th>{t('wallets_rewards_block')}</th>
                <th>{t('wallets_rewards_amount')}</th>
                <th>{t('chain_pol_score')}</th>
                <th>{t('wallets_rewards_timestamp')}</th>
              </tr>
            </thead>
            <tbody>
              {rewardHistory.length === 0 && (
                <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--terminal-muted)" }}>Aucun reward pour ce wallet.</td></tr>
              )}
              {rewardHistory.map((r) => (
                <tr key={r.block_index}>
                  <td>#{r.block_index}</td>
                  <td>{r.reward_artcb}</td>
                  <td>{r.pol_score?.toFixed(2)}</td>
                  <td>{r.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
