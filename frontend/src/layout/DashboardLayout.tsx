import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import axios from "axios";
import { chainQueryParams, fetchChain, fetchPolScore } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { LanguageSelector } from "../i18n/LanguageSelector";
import { useTranslation } from "../i18n/useTranslation";
import type { ChainBlock } from "../types";

export function DashboardLayout() {
  const { t } = useTranslation();
  const { visibility, setVisibility, groupId, chainBlock } = useDashboard();
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [polScore, setPolScore] = useState<number | null>(null);
  const [blocks, setBlocks] = useState<ChainBlock[]>([]);
  const [chainValid, setChainValid] = useState<boolean | null>(null);

  const NAV = [
    { section: "CORE", items: [
      { to: "/", label: t('nav_dashboard'), icon: "▶" },
      { to: "/memorize", label: t('nav_memorize'), icon: "✎" },
      { to: "/graph", label: t('nav_graph'), icon: "◎" },
    ]},
    { section: "CHAIN", items: [
      { to: "/chain", label: t('nav_chain'), icon: "▣" },
      { to: "/wallets", label: t('nav_wallets'), icon: "◇" },
      { to: "/mining", label: t('nav_mining'), icon: "⛏" },
    ]},
    { section: "SYSTEM", items: [
      { to: "/system", label: t('nav_system'), icon: "F3" },
      { to: "/logs", label: t('nav_logs'), icon: "≡" },
      { to: "/console", label: t('nav_console'), icon: "⌨" },
      { to: "/integrations", label: t('nav_integrations'), icon: "⚙" },
      { to: "/network", label: t('nav_network'), icon: "⇄" },
      { to: "/governance", label: t('nav_governance'), icon: "⚖" },
      { to: "/groups", label: t('nav_groups'), icon: "👥" },
      { to: "/api-keys", label: t('nav_api_keys'), icon: "🔑" },
      { to: "/agent-memory", label: t('nav_agent_memory'), icon: "🤖" },
    ]},
  ];

  useEffect(() => {
    const tick = async () => {
      try {
        await axios.get("/api/v1/health", { timeout: 3000 });
        setApiOk(true);
      } catch {
        setApiOk(false);
      }
      try {
        const pol = await fetchPolScore();
        setPolScore(pol.pol_score);
      } catch { /* keep last */ }
      try {
        const q = chainQueryParams(visibility, groupId);
        const chain = await fetchChain(q);
        setBlocks(chain);
      } catch { /* keep last */ }
      try {
        const { data } = await axios.get("/api/v1/chain/verify");
        setChainValid(data.valid ?? false);
      } catch {
        setChainValid(null);
      }
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, [visibility, groupId]);

  const lastBlock = chainBlock ?? blocks[blocks.length - 1] ?? null;

  return (
    <div className="mc-dashboard">
      <header className="mc-header">
        <div className="mc-header-left">
          <span className="mc-logo">ARTCB</span>
          <span className={`mc-api-badge${apiOk === false ? " mc-api-down" : ""}`}>
            {apiOk === null ? "…" : apiOk ? "+ API OK" : "X API DOWN"}
          </span>
          {polScore !== null && <span className="mc-header-kpi">◆ PoL {polScore.toFixed(2)}</span>}
          <span className="mc-header-kpi">▣ Blocs {blocks.length}</span>
          {chainValid !== null && (
            <span className="mc-header-kpi">{chainValid ? "Chain OK" : "Chain X"}</span>
          )}
        </div>
        <div className="mc-header-right">
          <label className="mc-network-select" aria-label="Sélecteur réseau">
            Réseau:
            <select
              value={visibility}
              aria-label="Visibilité réseau"
              onChange={(e) => setVisibility(e.target.value as "private" | "group" | "public")}
            >
              <option value="private">PRIVÉ</option>
              <option value="group">GROUPE{groupId ? ` (${groupId.slice(0, 8)}…)` : ""}</option>
              <option value="public">PUBLIC</option>
            </select>
          </label>
          <LanguageSelector />
          <span className="badge-debug">DEBUG</span>
          <Link to="/console" className="mc-console-link">⌨ CONSOLE</Link>
        </div>
      </header>

      <div className="mc-body">
        <nav className="mc-sidebar" aria-label="Navigation dashboard">
          {NAV.map((group) => (
            <div key={group.section} className="mc-nav-group">
              <div className="mc-nav-section">{group.section}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) => `mc-nav-item${isActive ? " mc-nav-active" : ""}`}
                >
                  <span className="mc-nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <main className="mc-main">
          <Outlet />
        </main>
      </div>

      <footer className="chain-footer mc-footer">
        <span>
          {lastBlock
            ? `Bloc #${lastBlock.index} · hash ${lastBlock.hash.slice(0, 8)}…`
            : "Aucun bloc"}
          {lastBlock?.pol_score != null && ` · PoL ${lastBlock.pol_score.toFixed(2)}`}
        </span>
      </footer>
    </div>
  );
}
