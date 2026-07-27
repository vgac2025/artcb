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

export function Wallets() {
  const { t } = useTranslation();
  const { setActorAddress } = useDashboard();
  const [wallets, setWallets] = useState<
    Array<{ address: string; name: string; balance?: number; rewards?: number }>
  >([]);
  const [founders, setFounders] = useState<Array<{ founder_id: number; name: string; balance_artcb: number }>>([]);
  const [newName, setNewName] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [rewardHistory, setRewardHistory] = useState<
    Array<{ block_index: number; reward_artcb: number; pol_score: number; timestamp: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const w = await createWallet(newName.trim());
      setActorAddress(w.address);
      setNewName("");
      await reload();
    } catch (err: unknown) {
      // Axios wraps HTTP errors — extraire le detail lisible
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

  const showRewards = async (address: string) => {
    setSelected(address);
    const r = await fetchWalletRewards(address);
    setRewardHistory(r.rewards);
  };

  const slots = Array.from({ length: 27 }, (_, i) => wallets[i] ?? null);

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('wallets_title')}</h1>

      <div className="panel">
        <h2>{t('wallets_create_title')}</h2>
        <div className="toolbar">
          <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={t('wallets_create_placeholder')} />
          <button className="primary" onClick={handleCreate} disabled={loading}>
            {t('wallets_create_button')}
          </button>
        </div>
        {error && <p className="mc-error">{error}</p>}
      </div>

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

      {founders.length > 0 && (
        <div className="panel">
          <h2>{t('wallets_founders_title')}</h2>
          <div className="mc-hotbar">
            {founders.map((f) => (
              <div key={f.founder_id} className="mc-slot mc-slot-gold">
                <div className="mc-kpi-label">{f.name}</div>
                <div className="mc-kpi-value">{f.balance_artcb.toLocaleString()} ₳</div>
              </div>
            ))}
          </div>
        </div>
      )}

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
