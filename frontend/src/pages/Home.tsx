import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  chainQueryParams,
  fetchChain,
  fetchDemoLiveLog,
  fetchHealth,
  fetchPolScore,
  fetchWallets,
} from "../api/client";
import { McBlockRow } from "../components/McBlockRow";
import { McKpiSlot } from "../components/McKpiSlot";
import { useDashboard } from "../context/DashboardContext";
import type { ChainBlock } from "../types";

const CHECKLIST = [
  { id: "memorized" as const, label: "Mémoriser un texte", to: "/memorize" },
  { id: "explored" as const, label: "Explorer le graphe", to: "/graph" },
  { id: "searched" as const, label: "Rechercher un nœud", to: "/graph" },
  { id: "signed" as const, label: "Reconstruire + signer bloc", to: "/chain" },
];

export function Home() {
  const { checklist, visibility, groupId } = useDashboard();
  const [pol, setPol] = useState<number | null>(null);
  const [blocks, setBlocks] = useState<ChainBlock[]>([]);
  const [walletCount, setWalletCount] = useState(0);
  const [chainValid, setChainValid] = useState(false);
  const [alerts, setAlerts] = useState<string[]>([]);
  const [demoOk, setDemoOk] = useState<boolean | null>(null);

  useEffect(() => {
    const q = chainQueryParams(visibility, groupId);
    fetchPolScore().then((p) => setPol(p.pol_score)).catch((e) => setAlerts((a) => [...a, `PoL: ${e}`]));
    fetchChain(q).then(setBlocks).catch((e) => setAlerts((a) => [...a, `Chain: ${e}`]));
    fetchWallets().then((w) => setWalletCount(w.length)).catch(() => setWalletCount(0));
    fetchHealth()
      .then((h) => {
        const chain = h.chain as { valid?: boolean } | undefined;
        setChainValid(chain?.valid ?? false);
        if (h.status !== "ok") setAlerts((a) => [...a, "API health not ok"]);
      })
      .catch(() => setAlerts((a) => [...a, "API /health timeout"]));
    fetchDemoLiveLog()
      .then((d) => setDemoOk(d.content.includes("DEMO COMPLETE")))
      .catch(() => setDemoOk(false));
  }, [visibility, groupId]);

  const heatmap = blocks.slice(-14).map((_, i) => (i % 3 === 0 ? "▓" : "░")).join("");

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">Accueil</h1>

      {alerts.length > 0 && (
        <div className="panel mc-debug-alerts">
          <h2>Alertes DEBUG</h2>
          {alerts.map((a, i) => (
            <p key={i} className="mc-error">
              [!] {a}
            </p>
          ))}
        </div>
      )}

      <div className="mc-hotbar">
        <McKpiSlot icon="PoL" label="PoL" value={pol?.toFixed(2) ?? "—"} barPct={(pol ?? 0) * 100} />
        <McKpiSlot icon="▣" label="Blocs" value={String(blocks.length)} sub={`réseau ${visibility}`} />
        <McKpiSlot icon="◇" label="Wallets" value={String(walletCount)} />
        <McKpiSlot icon="◎" label="Graphes" value={String(blocks.length)} sub="IR live" />
        <McKpiSlot icon="OK" label="Chain" value={chainValid ? "VALID OK" : "CHECK"} gold={chainValid} />
      </div>

      <div className="panel mc-checklist">
        <h2>Parcours rapide</h2>
        <ul className="mc-checklist-list">
          {CHECKLIST.map((item) => (
            <li key={item.id}>
              <span className="mc-check-box">{checklist[item.id] ? "[OK]" : "[ ]"}</span>
              <span>{item.label}</span>
              <Link to={item.to} className="mc-link-pill">
                → Aller
              </Link>
            </li>
          ))}
        </ul>
        {/* BUG-R5: hauteur fixe pour éviter layout shift quand demo_live charge */}
        <p className="mc-muted" style={{ height: "1.5em", overflow: "hidden", margin: 0 }}>
          {demoOk !== null
            ? <>Dernière demo_live : {demoOk ? "OK OK" : "non trouvée"} — <Link to="/logs">Logs</Link></>
            : "\u00a0"}
        </p>
      </div>

      <div className="panel">
        <h2>Activité blocs (heatmap)</h2>
        <p className="mc-heatmap" aria-label="heatmap blocs">
          {heatmap || "░░░░░░░░░░░░░░"}
        </p>
      </div>

      <div className="panel">
        <div className="mc-section-head">
          <h2>Derniers blocs</h2>
          <Link to="/chain" className="mc-link-pill">
            Voir tout →
          </Link>
        </div>
        <McBlockRow blocks={blocks} limit={6} />
        <p className="mc-muted mc-reward-note">Reward genesis epoch : 1 ARTCB / bloc</p>
      </div>
    </div>
  );
}
