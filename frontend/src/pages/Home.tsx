import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  chainQueryParams,
  fetchChain,
  fetchHealth,
  fetchPolScore,
  fetchWallets,
} from "../api/client";
// B7 FIX: fetchDemoLiveLog supprimé de Home.tsx — la page Logs gère déjà cet affichage
import { McBlockRow } from "../components/McBlockRow";
import { McKpiSlot } from "../components/McKpiSlot";
import { useDashboard } from "../context/DashboardContext";
import { useTranslation } from "../i18n/useTranslation";
import type { ChainBlock } from "../types";

export function Home() {
  const { t } = useTranslation();
  const { checklist, visibility, groupId } = useDashboard();
  const [pol, setPol] = useState<number | null>(null);
  const [blocks, setBlocks] = useState<ChainBlock[]>([]);
  const [walletCount, setWalletCount] = useState(0);
  const [chainValid, setChainValid] = useState(false);
  const [alerts, setAlerts] = useState<string[]>([]);
  const [demoOk] = useState<boolean | null>(null);
  // B7 FIX: fetchDemoLiveLog supprimé — inutile dans Home.tsx, Logs.tsx gère l'affichage

  useEffect(() => {
    const q = chainQueryParams(visibility, groupId);
    // Fetches parallèles — cohérent avec la correction B5 du DashboardLayout
    Promise.allSettled([
      fetchPolScore(),
      fetchChain(q),
      fetchWallets(),
      fetchHealth(),
    ]).then(([polR, chainR, walletsR, healthR]) => {
      if (polR.status === "fulfilled") setPol(polR.value.pol_score);
      else setAlerts((a) => [...a, `PoL: ${polR.reason}`]);

      if (chainR.status === "fulfilled") setBlocks(chainR.value);
      else setAlerts((a) => [...a, `Chain: ${chainR.reason}`]);

      if (walletsR.status === "fulfilled") setWalletCount(walletsR.value.length);

      if (healthR.status === "fulfilled") {
        const chain = healthR.value.chain as { valid?: boolean } | undefined;
        setChainValid(chain?.valid ?? false);
        if (healthR.value.status !== "ok") setAlerts((a) => [...a, "API health not ok"]);
      } else {
        setAlerts((a) => [...a, "API /health timeout"]);
      }
    });
  }, [visibility, groupId]);

  const heatmap = blocks.slice(-14).map((_, i) => (i % 3 === 0 ? "▓" : "░")).join("");

  const CHECKLIST = [
    { id: "memorized" as const, label: t('home_checklist_memorize'), to: "/memorize" },
    { id: "explored" as const, label: t('home_checklist_explore'), to: "/graph" },
    { id: "searched" as const, label: t('home_checklist_search'), to: "/graph" },
    { id: "signed" as const, label: t('home_checklist_sign'), to: "/chain" },
  ];

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('home_title')}</h1>

      {alerts.length > 0 && (
        <div className="panel mc-debug-alerts">
          <h2>{t('home_alerts_debug')}</h2>
          {alerts.map((a, i) => (
            <p key={i} className="mc-error">
              [!] {a}
            </p>
          ))}
        </div>
      )}

      <div className="mc-hotbar">
        <McKpiSlot icon="PoL" label={t('home_kpi_pol')} value={pol?.toFixed(2) ?? "—"} barPct={(pol ?? 0) * 100} />
        <McKpiSlot icon="▣" label={t('home_kpi_blocks')} value={String(blocks.length)} sub={`${t('home_kpi_network')} ${visibility}`} />
        <McKpiSlot icon="◇" label={t('home_kpi_wallets')} value={String(walletCount)} />
        <McKpiSlot icon="◎" label={t('home_kpi_graphs')} value={String(blocks.length)} sub={t('home_ir_live')} />
        <McKpiSlot icon="OK" label={t('home_kpi_chain')} value={chainValid ? t('home_chain_valid') : t('home_chain_check')} gold={chainValid} />
      </div>

      <div className="panel mc-checklist">
        <h2>{t('home_checklist_title')}</h2>
        <ul className="mc-checklist-list">
          {CHECKLIST.map((item) => (
            <li key={item.id}>
              <span className="mc-check-box">{checklist[item.id] ? "[OK]" : "[ ]"}</span>
              <span>{item.label}</span>
              <Link to={item.to} className="mc-link-pill">
                {t('home_checklist_goto')}
              </Link>
            </li>
          ))}
        </ul>
        {/* BUG-R5: hauteur fixe pour éviter layout shift quand demo_live charge */}
        <p className="mc-muted" style={{ height: "1.5em", overflow: "hidden", margin: 0 }}>
          {demoOk !== null
            ? <>{t('home_demo_last')} {demoOk ? t('home_demo_ok') : t('home_demo_not_found')} — <Link to="/logs">Logs</Link></>
            : "\u00a0"}
        </p>
      </div>

      <div className="panel">
        <h2>{t('home_activity_heatmap')}</h2>
        <p className="mc-heatmap" aria-label="heatmap blocs">
          {heatmap || "░░░░░░░░░░░░░░"}
        </p>
      </div>

      <div className="panel">
        <div className="mc-section-head">
          <h2>{t('home_latest_blocks')}</h2>
          <Link to="/chain" className="mc-link-pill">
            {t('home_view_all')}
          </Link>
        </div>
        <McBlockRow blocks={blocks} limit={6} />
        <p className="mc-muted mc-reward-note">{t('home_reward_note')}</p>
      </div>
    </div>
  );
}
