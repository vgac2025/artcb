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

  const inp: React.CSSProperties = {
    width: "100%", padding: "8px 10px", borderRadius: 6,
    border: "1px solid #e5e7eb", fontSize: 14, boxSizing: "border-box",
  };
  const btn = (color = "#3b82d4"): React.CSSProperties => ({
    background: color, color: "#fff", border: "none", borderRadius: 6,
    padding: "8px 18px", cursor: "pointer", fontSize: 14, fontWeight: 600,
  });

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <h2 style={{ marginBottom: 4 }}>{t('agent_memory_title')}</h2>
      <p style={{ color: "#57606a", fontSize: 14, marginBottom: 16 }}>
        Interface complète pour que Bob/Cursor/ChatGPT utilise ARTCB comme mémoire persistante
      </p>

      {/* Token Bearer */}
      <div style={{ background: "#f7f8fa", border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 16 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: "#57606a" }}>Bearer Token (optionnel)</label>
        <input
          style={{ ...inp, marginTop: 4, fontFamily: "monospace" }}
          type="password"
          placeholder="artcb_xxxxxxxx… (généré dans Clés API)"
          value={token}
          onChange={e => setToken(e.target.value)}
        />
      </div>

      {/* Onglets */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 20 }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer",
              background: tab === t.id ? "#3b82d4" : "#e5e7eb",
              color: tab === t.id ? "#fff" : "#1f2328",
              fontWeight: 600, fontSize: 13,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div style={{ color: "#dc2626", background: "#fef2f2", padding: 10, borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {success && <div style={{ color: "#16a34a", background: "#f0fdf4", padding: 10, borderRadius: 6, marginBottom: 12 }}>{success}</div>}

      {/* STATUS */}
      {tab === "status" && (
        <div>
          <button style={btn()} onClick={loadStatus} disabled={loading}>Rafraichir</button>
          {status && (
            <pre style={{ background: "#f7f8fa", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginTop: 12, fontSize: 13, overflow: "auto" }}>
              {JSON.stringify(status, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* MÉMOIRE */}
      {tab === "memos" && (
        <div>
          <button style={btn()} onClick={loadMemos} disabled={loading}>Rafraichir</button>
          <div style={{ marginTop: 12 }}>
            {memos.length === 0 && <p style={{ color: "#57606a" }}>Aucun mémo IA gravé pour l'instant.</p>}
            {memos.map(m => (
              <div key={m.block_index} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  {badge(m.memo_type, "#7c5cd8")}
                  {badge(`Bloc #${m.block_index}`, "#3b82d4")}
                  {badge(`PoL ${m.pol_score.toFixed(3)}`, m.pol_score > 0.8 ? "#16a34a" : "#f59e0b")}
                  <span style={{ fontSize: 12, color: "#57606a" }}>{m.timestamp}</span>
                </div>
                <div style={{ fontSize: 12, color: "#57606a" }}>
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
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <textarea
            style={{ ...inp, minHeight: 120, resize: "vertical" }}
            placeholder="Observation, bug, fix, décision, leçon apprise…"
            value={memoContent}
            onChange={e => setMemoContent(e.target.value)}
          />
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <select style={{ ...inp, width: "auto" }} value={memoType} onChange={e => setMemoType(e.target.value)}>
              {["observation", "bug", "fix", "lesson", "decision", "hypothesis", "goal", "proof"].map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <input style={{ ...inp, flex: 1 }} placeholder="Tags (virgule séparés)" value={memoTags} onChange={e => setMemoTags(e.target.value)} />
            <input style={{ ...inp, flex: 1 }} placeholder="Session ID" value={memoSession} onChange={e => setMemoSession(e.target.value)} />
          </div>
          <button style={btn("#7c5cd8")} onClick={submitMemo} disabled={loading || !memoContent.trim()}>
            Graver dans la blockchain
          </button>
        </div>
      )}

      {/* RECHERCHE */}
      {tab === "search" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input style={{ ...inp, flex: 1 }} placeholder="Terme à rechercher dans toute la chaîne…" value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} />
            <button style={btn()} onClick={doSearch} disabled={loading}>Rechercher</button>
          </div>
          {searchResults.map((r, i) => (
            <div key={i} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10, marginBottom: 8, fontSize: 13 }}>
              <b>Score:</b> {String((r.score as number | undefined)?.toFixed(4) ?? "—")} · <b>Graph:</b> {String(r.graph_id ?? "—").slice(0, 20)}…
              {r.block != null && <> · <b>Bloc:</b> #{String((r.block as Record<string, unknown>)?.block_index ?? "—")}</>}
              <div style={{ color: "#57606a", marginTop: 4 }}>{String(r.text ?? r.label ?? "").slice(0, 200)}</div>
            </div>
          ))}
          {searchResults.length === 0 && searchQ && <p style={{ color: "#57606a" }}>Aucun résultat.</p>}
        </div>
      )}

      {/* EXPORT */}
      {tab === "export" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
            <select style={{ ...inp, width: 140 }} value={exportFmt} onChange={e => setExportFmt(e.target.value as typeof exportFmt)}>
              <option value="summary">Summary</option>
              <option value="jsonl">JSONL (RAG)</option>
              <option value="json">JSON complet</option>
            </select>
            <button style={btn()} onClick={doExport} disabled={loading}>Exporter</button>
            {exportData && (
              <button style={btn("#16a34a")} onClick={() => navigator.clipboard?.writeText(exportData)}>Copier</button>
            )}
          </div>
          {exportData && (
            <pre style={{ background: "#f7f8fa", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, fontSize: 12, overflow: "auto", maxHeight: 400 }}>
              {exportData.slice(0, 8000)}{exportData.length > 8000 ? "\n…(tronqué)" : ""}
            </pre>
          )}
        </div>
      )}

      {/* WEBHOOKS */}
      {tab === "webhooks" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <input style={{ ...inp, flex: 2 }} placeholder="URL HTTPS (https://…)" value={whUrl} onChange={e => setWhUrl(e.target.value)} />
            <input style={{ ...inp, flex: 1 }} placeholder="Label" value={whLabel} onChange={e => setWhLabel(e.target.value)} />
            <button style={btn()} onClick={addWebhook} disabled={loading || !whUrl || !whLabel}>+ Ajouter</button>
          </div>
          {webhooks.map(h => (
            <div key={String(h.hook_id)} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <b>{String(h.label)}</b> <span style={{ color: "#57606a", fontSize: 12 }}>{String(h.url)}</span>
                <div style={{ fontSize: 12, color: "#57606a" }}>Events: {(h.events as string[])?.join(", ")}</div>
              </div>
              <button style={{ ...btn("#dc2626"), padding: "4px 12px" }} onClick={() => removeWebhook(String(h.hook_id))}>X</button>
            </div>
          ))}
        </div>
      )}

      {/* STREAM THOUGHT */}
      {tab === "stream" && (
        <div>
          <p style={{ color: "#57606a", fontSize: 13, marginBottom: 12 }}>
            Connecte un WebSocket <code>/ws/stream_thought</code> — envoie des tokens en temps réel → grave le raisonnement complet en un seul bloc PoL.
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {streamStatus === "idle" && <button style={btn("#16a34a")} onClick={openStream}>Ouvrir le stream</button>}
            {streamStatus === "open" && <>
              <input style={{ ...inp, flex: 1 }} placeholder="Texte a streamer..." value={streamInput} onChange={e => setStreamInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendTokens()} />
              <button style={btn()} onClick={sendTokens}>Envoyer tokens</button>
              <button style={btn("#7c5cd8")} onClick={commitStream}>Graver</button>
              <button style={btn("#dc2626")} onClick={abortStream}>Annuler</button>
            </>}
            {(streamStatus === "done" || streamStatus === "committing") && (
              <button style={btn("#57606a")} onClick={() => { setStreamStatus("idle"); setStreamLog([]); if (wsRef.current) wsRef.current.close(); }}>Reinitialiser</button>
            )}
          </div>
          <div style={{ background: "#0d1117", borderRadius: 8, padding: 12, minHeight: 120, maxHeight: 300, overflow: "auto", fontFamily: "monospace", fontSize: 13, color: "#e6edf3" }}>
            {streamLog.length === 0 ? <span style={{ color: "#57606a" }}>— En attente de connexion…</span> : streamLog.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        </div>
      )}
    </div>
  );
}
