import { useEffect, useRef, useState } from "react";
import {
  fetchAiStatus,
  fetchAiMemory,
  postAiMemo,
  chainSearch,
  chainExport,
  fetchWebhooks,
  registerWebhook,
  deleteWebhook,
  type AiMemo,
} from "../api/client";
import { useTranslation } from "../i18n/useTranslation";

type Tab = "status" | "memos" | "memo_new" | "search" | "export" | "webhooks" | "stream";

function badge(text: string, color: string) {
  return (
    <span
      style={{
        background: color,
        color: "#fff",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        marginRight: 4,
      }}
    >
      {text}
    </span>
  );
}

export function AgentMemory() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("status");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [memos, setMemos] = useState<AiMemo[]>([]);
  const [searchQ, setSearchQ] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [searchResults, setSearchResults] = useState<Record<string, unknown>[]>([]);
  const [exportData, setExportData] = useState<string>("");
  const [exportFmt, setExportFmt] = useState<"jsonl" | "json" | "summary">("summary");
  const [webhooks, setWebhooks] = useState<Record<string, unknown>[]>([]);
  const [whUrl, setWhUrl] = useState("");
  const [whLabel, setWhLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Nouveau mémo
  const [memoContent, setMemoContent] = useState("");
  const [memoType, setMemoType] = useState("observation");
  const [memoTags, setMemoTags] = useState("");
  const [memoSession, setMemoSession] = useState("agent_session");

  // Stream thought
  const [streamStatus, setStreamStatus] = useState<"idle" | "open" | "committing" | "done">("idle");
  const [streamLog, setStreamLog] = useState<string[]>([]);
  const [streamInput, setStreamInput] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const auth = token.trim() || undefined;

  const clear = () => { setError(null); setSuccess(null); };

  const loadStatus = async () => {
    clear(); setLoading(true);
    try { setStatus(await fetchAiStatus(auth)); }
    catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const loadMemos = async () => {
    clear(); setLoading(true);
    try { const r = await fetchAiMemory({ limit: 50 }, auth); setMemos(r.memos); }
    catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const loadWebhooks = async () => {
    clear(); setLoading(true);
    try { const r = await fetchWebhooks(auth); setWebhooks(r.webhooks); }
    catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (tab === "status") loadStatus();
    if (tab === "memos") loadMemos();
    if (tab === "webhooks") loadWebhooks();
  }, [tab]);

  const submitMemo = async () => {
    clear(); setLoading(true);
    try {
      const r = await postAiMemo({
        content: memoContent,
        memo_type: memoType,
        tags: memoTags ? memoTags.split(",").map(t => t.trim()) : [],
        session_id: memoSession,
        visibility: "private",
      }, auth);
      setSuccess(`Memo grave — bloc #${(r as Record<string, number>).block_index}`);
      setMemoContent("");
      setTab("memos");
      loadMemos();
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const doSearch = async () => {
    if (!searchQ.trim()) return;
    clear(); setLoading(true);
    try {
      const r = await chainSearch(searchQ, { top_k: 10 }, auth);
      setSearchResults(r.results);
      setHasSearched(true);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const doExport = async () => {
    clear(); setLoading(true);
    try {
      const r = await chainExport({ format: exportFmt }, auth);
      setExportData(String(r.data));
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const addWebhook = async () => {
    if (!whUrl || !whLabel) return;
    clear(); setLoading(true);
    try {
      await registerWebhook({ url: whUrl, label: whLabel, events: ["block_stored"] }, auth);
      setSuccess("Webhook enregistre");
      setWhUrl(""); setWhLabel("");
      loadWebhooks();
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const removeWebhook = async (id: string) => {
    clear();
    try {
      await deleteWebhook(id, auth);
      loadWebhooks();
    } catch (e) { setError(String(e)); }
  };

  // WebSocket stream_thought
  const openStream = () => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/stream_thought`);
    wsRef.current = ws;
    ws.onopen = () => {
      setStreamStatus("open");
      setStreamLog(prev => [...prev, "[OK] Connexion WebSocket ouverte"]);
      ws.send(JSON.stringify({ type: "start", agent_id: auth ? "bob_agent" : "anonymous", memo_type: "reasoning" }));
    };
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "token_ack") {
        setStreamLog(prev => [...prev.slice(-50), `  … ${msg.count} tokens en buffer`]);
      } else if (msg.type === "committed") {
        setStreamStatus("done");
        setStreamLog(prev => [...prev, `[OK] ${msg.message}`]);
      } else {
        setStreamLog(prev => [...prev, JSON.stringify(msg)]);
      }
    };
    ws.onclose = () => setStreamLog(prev => [...prev, "[CLOSED] Connexion fermée"]);
    ws.onerror = () => setStreamLog(prev => [...prev, "[ERR] Erreur WebSocket"]);
  };

  const sendTokens = () => {
    if (!wsRef.current || !streamInput.trim()) return;
    const words = streamInput.trim().split(/\s+/);
    for (const w of words) {
      wsRef.current.send(JSON.stringify({ type: "token", text: w + " " }));
    }
    setStreamLog(prev => [...prev, `[SEND] ${words.length} tokens envoyes`]);
    setStreamInput("");
  };

  const commitStream = () => {
    if (!wsRef.current) return;
    setStreamStatus("committing");
    wsRef.current.send(JSON.stringify({ type: "commit", visibility: "private" }));
  };

  const abortStream = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: "abort" }));
      wsRef.current.close();
    }
    setStreamStatus("idle");
    setStreamLog([]);
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "status", label: t('agent_memory_tab_status') },
    { id: "memos", label: t('agent_memory_tab_memos') },
    { id: "memo_new", label: t('agent_memory_tab_new') },
    { id: "search", label: t('agent_memory_tab_search') },
    { id: "export", label: t('agent_memory_tab_export') },
    { id: "webhooks", label: t('agent_memory_tab_webhooks') },
    { id: "stream", label: t('agent_memory_tab_stream') },
  ];

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('agent_memory_title')}</h1>
      <p className="mc-muted" style={{ marginBottom: 16 }}>
        Interface memoire persistante IA — Bob / Cursor / ChatGPT utilisent ARTCB comme backend.
      </p>

      {/* Token Bearer */}
      <div className="panel">
        <label className="mc-label">Bearer Token (optionnel)</label>
        <input
          style={{ marginTop: 4, fontFamily: "monospace", width: "100%" }}
          type="password"
          placeholder="artcb_xxxxxxxx... (genere dans Cles API)"
          value={token}
          onChange={e => setToken(e.target.value)}
        />
      </div>

      {/* Onglets MC */}
      <div className="toolbar" style={{ flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
        {tabs.map(tab_ => (
          <button
            key={tab_.id}
            onClick={() => setTab(tab_.id)}
            className={tab === tab_.id ? "primary" : ""}
          >
            {tab_.label}
          </button>
        ))}
      </div>

      {error   && <p className="mc-error"   style={{ marginBottom: 12 }}>{error}</p>}
      {success && <p className="mc-success" style={{ marginBottom: 12 }}>{success}</p>}

      {/* STATUS */}
      {tab === "status" && (
        <div className="panel">
          <div className="toolbar"><button onClick={loadStatus} disabled={loading}>Rafraichir</button></div>
          {status && (
            <pre className="mc-console" style={{ marginTop: 12, maxHeight: 400, overflow: "auto" }}>
              {JSON.stringify(status, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* MÉMOIRE */}
      {tab === "memos" && (
        <div className="panel">
          <div className="toolbar"><button onClick={loadMemos} disabled={loading}>Rafraichir</button></div>
          <div style={{ marginTop: 12 }}>
            {memos.length === 0 && <p className="mc-muted">Aucun memo IA grave pour l'instant.</p>}
            {memos.map(m => (
              <div key={m.block_index} className="panel" style={{ marginBottom: 8, padding: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  {badge(m.memo_type, "#7c5cd8")}
                  {badge(`Bloc #${m.block_index}`, "#3b82d4")}
                  {badge(`PoL ${m.pol_score.toFixed(3)}`, m.pol_score > 0.8 ? "#16a34a" : "#f59e0b")}
                  <span className="mc-muted" style={{ fontSize: 12 }}>{m.timestamp}</span>
                </div>
                <div className="mc-muted" style={{ fontSize: 12 }}>
                  Agent: <b>{m.agent_id}</b> · Session: {m.session_id} · Graph: {m.graph_id.slice(0, 16)}…
                  {m.tags.length > 0 && <> · Tags: {m.tags.join(", ")}</>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* NOUVEAU MÉMO */}
      {tab === "memo_new" && (
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <textarea
            className="mc-input"
            style={{ minHeight: 120, resize: "vertical" }}
            placeholder="Observation, bug, fix, decision, lecon apprise..."
            value={memoContent}
            onChange={e => setMemoContent(e.target.value)}
          />
          <div className="toolbar" style={{ flexWrap: "wrap" }}>
            <select value={memoType} onChange={e => setMemoType(e.target.value)}>
              {["observation", "bug", "fix", "lesson", "decision", "hypothesis", "goal", "proof"].map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <input placeholder="Tags (virgule separes)" value={memoTags} onChange={e => setMemoTags(e.target.value)} style={{ flex: 1 }} />
            <input placeholder="Session ID" value={memoSession} onChange={e => setMemoSession(e.target.value)} style={{ flex: 1 }} />
          </div>
          <button className="primary" onClick={submitMemo} disabled={loading || !memoContent.trim()}>
            Graver dans la blockchain
          </button>
        </div>
      )}

      {/* RECHERCHE */}
      {tab === "search" && (
        <div className="panel">
          <div className="toolbar" style={{ marginBottom: 12 }}>
            <input style={{ flex: 1 }} placeholder="Terme a rechercher dans toute la chaine..." value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} />
            <button className="primary" onClick={doSearch} disabled={loading}>Rechercher</button>
          </div>
          {searchResults.map((r, i) => (
            <div key={i} className="panel" style={{ marginBottom: 8, padding: 10, fontSize: 13 }}>
              <b>Score:</b> {String((r.score as number | undefined)?.toFixed(4) ?? "—")} · <b>Graph:</b> {String(r.graph_id ?? "—").slice(0, 20)}…
              {r.block != null && <> · <b>Bloc:</b> #{String((r.block as Record<string, unknown>)?.block_index ?? "—")}</>}
              <div className="mc-muted" style={{ marginTop: 4 }}>{String(r.text ?? r.label ?? "").slice(0, 200)}</div>
            </div>
          ))}
          {searchResults.length === 0 && hasSearched && <p className="mc-muted">Aucun resultat.</p>}
        </div>
      )}

      {/* EXPORT */}
      {tab === "export" && (
        <div className="panel">
          <div className="toolbar" style={{ marginBottom: 12, alignItems: "center" }}>
            <select value={exportFmt} onChange={e => setExportFmt(e.target.value as typeof exportFmt)}>
              <option value="summary">Summary</option>
              <option value="jsonl">JSONL (RAG)</option>
              <option value="json">JSON complet</option>
            </select>
            <button onClick={doExport} disabled={loading}>Exporter</button>
            {exportData && (
              <button onClick={() => navigator.clipboard?.writeText(exportData)}>Copier</button>
            )}
          </div>
          {exportData && (
            <pre className="mc-console" style={{ fontSize: 12, maxHeight: 400, overflow: "auto" }}>
              {exportData.slice(0, 8000)}{exportData.length > 8000 ? "\n...(tronque)" : ""}
            </pre>
          )}
        </div>
      )}

      {/* WEBHOOKS */}
      {tab === "webhooks" && (
        <div className="panel">
          <div className="toolbar" style={{ marginBottom: 12, flexWrap: "wrap" }}>
            <input style={{ flex: 2 }} placeholder="URL HTTPS (https://...)" value={whUrl} onChange={e => setWhUrl(e.target.value)} />
            <input style={{ flex: 1 }} placeholder="Label" value={whLabel} onChange={e => setWhLabel(e.target.value)} />
            <button onClick={addWebhook} disabled={loading || !whUrl || !whLabel}>+ Ajouter</button>
          </div>
          {webhooks.map(h => (
            <div key={String(h.hook_id)} className="panel" style={{ marginBottom: 8, padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <b>{String(h.label)}</b> <span className="mc-muted" style={{ fontSize: 12 }}>{String(h.url)}</span>
                <div className="mc-muted" style={{ fontSize: 12 }}>Events: {(h.events as string[])?.join(", ")}</div>
              </div>
              <button onClick={() => removeWebhook(String(h.hook_id))} style={{ padding: "4px 12px", background: "var(--mc-redstone, #ff4757)" }}>X</button>
            </div>
          ))}
        </div>
      )}

      {/* STREAM THOUGHT */}
      {tab === "stream" && (
        <div className="panel">
          <p className="mc-muted" style={{ marginBottom: 12 }}>
            WebSocket <code>/ws/stream_thought</code> — tokens en temps reel → bloc PoL unique.
          </p>
          <div className="toolbar" style={{ marginBottom: 12 }}>
            {streamStatus === "idle" && <button className="primary" onClick={openStream}>Ouvrir le stream</button>}
            {streamStatus === "open" && <>
              <input style={{ flex: 1 }} placeholder="Texte a streamer..." value={streamInput} onChange={e => setStreamInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendTokens()} />
              <button onClick={sendTokens}>Envoyer tokens</button>
              <button className="primary" onClick={commitStream}>Graver</button>
              <button onClick={abortStream} style={{ background: "var(--mc-redstone, #ff4757)" }}>Annuler</button>
            </>}
            {(streamStatus === "done" || streamStatus === "committing") && (
              <button onClick={() => { setStreamStatus("idle"); setStreamLog([]); if (wsRef.current) wsRef.current.close(); }}>Reinitialiser</button>
            )}
          </div>
          <div className="mc-console" style={{ minHeight: 120, maxHeight: 300, overflow: "auto" }}>
            {streamLog.length === 0
              ? <span className="mc-muted">— En attente de connexion...</span>
              : streamLog.map((l, i) => <div key={i}>{l}</div>)
            }
          </div>
        </div>
      )}
    </div>
  );
}
