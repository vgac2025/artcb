import { useEffect, useState } from "react";
import {
  castGovernanceVote,
  createGovernanceProposal,
  fetchGovernanceProposals,
  fetchWallets,
} from "../api/client";
import { useTranslation } from "../i18n/useTranslation";

type Proposal = {
  proposal_id: string;
  title: string;
  description: string;
  version: string;
  status: string;
  tally?: {
    yes: number;
    no: number;
    total: number;
    majority_yes: boolean;
    requires_rollback: boolean;
  };
};

export function Governance() {
  const { t } = useTranslation();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [wallets, setWallets] = useState<Array<{ address: string; name: string }>>([]);
  const [walletAddress, setWalletAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("0.4.0");

  const reload = async () => {
    try {
      const data = await fetchGovernanceProposals();
      setProposals(data.proposals as Proposal[]);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      reload(),
      fetchWallets().then((w) => {
        setWallets(w);
        if (w[0]) setWalletAddress(w[0].address);
      }).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const handleVote = async (proposalId: string, choice: "yes" | "no") => {
    if (!walletAddress) {
      setError("Sélectionnez un wallet pour voter");
      return;
    }
    setError(null);
    try {
      const r = await castGovernanceVote(proposalId, walletAddress, choice);
      setSuccess(`Vote ${choice} enregistré — rollback requis: ${r.requires_rollback ? "oui" : "non"}`);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleCreate = async () => {
    try {
      await createGovernanceProposal({ title, description, version });
      setSuccess("Proposition créée");
      setTitle("");
      setDescription("");
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="mc-page" aria-label="Page gouvernance">
      <h1 className="dashboard-title">{t('nav_governance')}</h1>
      <p className="mc-hint">
        1 wallet = 1 voix. Les mises à jour majeures VGACTech peuvent être acceptées ou rejetées par la communauté.
      </p>
      {loading && <p className="mc-muted" aria-live="polite">{t('loading')}</p>}
      {error && <p className="mc-error" role="alert">{error}</p>}
      {success && <p className="mc-success" aria-live="polite">{success}</p>}

      <section className="mc-card">
        <h2>Votre wallet votant</h2>
        <select value={walletAddress} onChange={(e) => setWalletAddress(e.target.value)}>
          {wallets.map((w) => (
            <option key={w.address} value={w.address}>{w.name} — {w.address.slice(0, 16)}…</option>
          ))}
        </select>
      </section>

      <section className="mc-card" aria-live="polite" aria-label="Liste des propositions">
        <h2>Propositions ({proposals.length})</h2>
        {!loading && proposals.length === 0 && (
          <p className="mc-muted">Aucune proposition ouverte pour le moment.</p>
        )}
        <ul className="mc-connector-list">
          {proposals.map((p) => (
            <li key={p.proposal_id} className="mc-connector-item">
              <strong>{p.title}</strong> — v{p.version} — {p.status}
              <p>{p.description}</p>
              {p.tally && (
                <p>Oui: {p.tally.yes} · Non: {p.tally.no} · Majorité oui: {p.tally.majority_yes ? "OK" : "X"}</p>
              )}
              {p.status === "open" && (
                <div className="mc-connector-actions">
                  <button type="button" className="mc-btn-sm" onClick={() => handleVote(p.proposal_id, "yes")}>Oui</button>
                  <button type="button" className="mc-btn-sm" onClick={() => handleVote(p.proposal_id, "no")}>Non</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="mc-card">
        <h2>Nouvelle proposition (VGACTech)</h2>
        <label>Titre<input value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>Description<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} /></label>
        <label>Version<input value={version} onChange={(e) => setVersion(e.target.value)} /></label>
        <button type="button" className="mc-btn" onClick={handleCreate} disabled={title.length < 3}>Créer</button>
      </section>
    </div>
  );
}
