import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchGroupByJoinCode,
  fetchWallets,
  signJoinWithWallet,
} from "../api/client";
import { useTranslation } from "../i18n/useTranslation";

export function JoinGroup() {
  const { t } = useTranslation();
  const [joinCode, setJoinCode] = useState("");
  const [groupInfo, setGroupInfo] = useState<{ name: string; group_id: string } | null>(null);
  const [wallets, setWallets] = useState<Array<{ address: string; name: string }>>([]);
  const [walletName, setWalletName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWallets()
      .then((w) => {
        setWallets(w);
        if (w.length) setWalletName(w[0].name ?? w[0].address);
      })
      .catch(() => setWallets([]));
  }, []);

  const lookupCode = async () => {
    setError(null);
    setGroupInfo(null);
    if (!joinCode.trim()) return;
    try {
      const info = await fetchGroupByJoinCode(joinCode.trim());
      setGroupInfo(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Code invalide");
    }
  };

  const submitRequest = async () => {
    if (!joinCode.trim() || !walletName) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await signJoinWithWallet(walletName, joinCode.trim());
      setMessage(res.message + ` — request ${res.request.request_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur demande");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">
        {t('nav_groups')}{" "}
        <Link to="/groups" className="mc-link-pill">
          ← Groupes
        </Link>
      </h1>

      <div className="panel">
        <h2>Demande d&apos;adhésion (Solution 2)</h2>
        <p className="mc-muted">
          L&apos;inviteur partage uniquement le <strong>code groupe</strong> — jamais votre clé privée.
          Vous signez avec votre wallet local ; l&apos;admin voit votre adresse seulement après validation.
        </p>
        <div className="toolbar">
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            placeholder="Code groupe (8 car.)"
            maxLength={8}
          />
          <button onClick={lookupCode}>Vérifier code</button>
        </div>
        {groupInfo && (
          <p className="mc-muted">
            Groupe trouvé : <strong>{groupInfo.name}</strong> ({groupInfo.group_id})
          </p>
        )}
      </div>

      <div className="panel">
        <h2>{t('common_wallet')}</h2>
        {wallets.length ? (
          <select value={walletName} onChange={(e) => setWalletName(e.target.value)}>
            {wallets.map((w) => (
              <option key={w.address} value={w.name ?? w.address}>
                {w.name ?? w.address.slice(0, 12)}…
              </option>
            ))}
          </select>
        ) : (
          <p className="mc-muted">
            Créez un wallet sur <Link to="/wallets">Wallets</Link> d&apos;abord.
          </p>
        )}
        <div className="toolbar">
          <button className="primary" onClick={submitRequest} disabled={loading || !joinCode}>
            {loading ? t('memorize_sign_loading') : "Signer et demander à rejoindre"}
          </button>
        </div>
        {message && <p className="mc-muted">{message}</p>}
        {error && <p className="mc-error">{error}</p>}
      </div>
    </div>
  );
}
