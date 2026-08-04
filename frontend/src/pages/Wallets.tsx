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
  const { setActorAddress } = useDashboard();
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
  const [copied, setCopied]               = useState(false);

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
        <div className="mc-chest-grid">
          {slots.map((w, i) => (
            <div
              key={i}
              className={`mc-chest-slot${w ? " mc-chest-filled" : ""}`}
              onClick={() => w && showRewards(w.address)}
              onKeyDown={(e) => e.key === "Enter" && w && showRewards(w.address)}
              role={w ? "button" : undefined}
              tabIndex={w ? 0 : undefined}
            >
              {w ? (
                <>
                  <div className="mc-chest-icon">◇</div>
                  <div className="mc-chest-name">{w.name}</div>
                  <div className="mc-gold-text">{(w.balance ?? 0).toFixed(2)} ₳</div>
                  <div className="mc-mono mc-chest-addr">{w.address.slice(0, 8)}…</div>
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
