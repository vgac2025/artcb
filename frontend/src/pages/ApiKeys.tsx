import { useEffect, useState } from "react";
import { generateApiKey, listApiKeys, revokeApiKey, type ApiKeyRecord } from "../api/client";
import { useTranslation } from "../i18n/useTranslation";

const SCOPE_OPTIONS = ["read", "write", "mining", "admin"];

function ts(epoch: number) {
  return new Date(epoch * 1000).toLocaleString();
}

export function ApiKeys() {
  const { t } = useTranslation();
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [label, setLabel] = useState("");
  const [scopes, setScopes] = useState<string[]>(["read", "write"]);
  const [expiresDays, setExpiresDays] = useState<string>("");
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = async () => {
    try {
      const res = await listApiKeys();
      setKeys(res.keys);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    reload();
  }, []);

  const handleGenerate = async () => {
    if (!label.trim()) return;
    setLoading(true);
    setError(null);
    setNewToken(null);
    setCopied(false);
    try {
      const res = await generateApiKey({
        label: label.trim(),
        scopes,
        expires_days: expiresDays ? parseInt(expiresDays, 10) : null,
      });
      setNewToken(res.token);
      setLabel("");
      setExpiresDays("");
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await revokeApiKey(keyId);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleCopy = () => {
    if (!newToken) return;
    navigator.clipboard.writeText(newToken).then(() => setCopied(true));
  };

  const toggleScope = (s: string) => {
    setScopes((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('api_keys_title')}</h1>
      <p className="mc-hint">
        Générez un token <code>artcb_…</code> pour connecter <strong>Cursor</strong>,{" "}
        <strong>ChatGPT Custom GPT</strong>, <strong>LangChain</strong> ou tout outil externe.{" "}
        Utilisez <code>Authorization: Bearer artcb_…</code> dans vos requêtes.
      </p>

      {error && <p className="mc-error">{error}</p>}

      {/* Alerte token — affiché UNE seule fois */}
      {newToken && (
        <div className="panel" style={{ border: "2px solid var(--mc-gold)" }}>
          <h2 className="mc-gold-text">⚠ {t('api_keys_token_warning')}</h2>
          <p className="mc-mono" style={{ wordBreak: "break-all", fontSize: "0.85rem" }}>
            {newToken}
          </p>
          <button className="mc-btn" onClick={handleCopy}>
            {copied ? "✓ Copié !" : "Copier"}
          </button>
          <button
            className="mc-btn-sm"
            style={{ marginLeft: "0.5rem" }}
            onClick={() => setNewToken(null)}
          >
            Fermer
          </button>
          <p className="mc-muted" style={{ marginTop: "0.5rem" }}>
            Exemple Cursor / VS Code :{" "}
            <code>ARTCB_API_KEY={newToken}</code>
          </p>
          <p className="mc-muted">
            Exemple curl :{" "}
            <code>
              curl -H "Authorization: Bearer {newToken}" https://&lt;host&gt;/api/v1/api-keys/me
            </code>
          </p>
        </div>
      )}

      {/* Formulaire génération */}
      <section className="mc-card">
        <h2>{t('api_keys_new_key')}</h2>
        <label>
          Nom de la clé
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Cursor dev, ChatGPT bot, LangChain…"
          />
        </label>

        <label>
          Droits (scopes)
          <div className="toolbar" style={{ flexWrap: "wrap", gap: "0.5rem", marginTop: "0.25rem" }}>
            {SCOPE_OPTIONS.map((s) => (
              <label key={s} style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                <input
                  type="checkbox"
                  checked={scopes.includes(s)}
                  onChange={() => toggleScope(s)}
                />
                {s}
              </label>
            ))}
          </div>
        </label>

        <label>
          Expiration (jours, vide = illimitée)
          <input
            type="number"
            value={expiresDays}
            onChange={(e) => setExpiresDays(e.target.value)}
            placeholder="365"
            min={1}
            max={3650}
            style={{ width: "8rem" }}
          />
        </label>

        <button
          type="button"
          className="mc-btn primary"
          onClick={handleGenerate}
          disabled={loading || label.trim().length === 0 || scopes.length === 0}
        >
          {loading ? "Génération…" : "Générer la clé"}
        </button>
      </section>

      {/* Liste des clés */}
      <section className="mc-card">
        <h2>{t('api_keys_active')} ({keys.filter((k) => k.active).length})</h2>
        {keys.length === 0 && (
          <p className="mc-muted">Aucune clé — créez-en une pour connecter vos outils.</p>
        )}
        <ul className="mc-connector-list">
          {keys.map((k) => (
            <li
              key={k.key_id}
              className={`mc-connector-item${k.active ? "" : " mc-muted"}`}
            >
              <strong>{k.label}</strong>
              {!k.active && <span className="mc-error"> [RÉVOQUÉE]</span>}
              <p className="mc-mono" style={{ fontSize: "0.8rem" }}>
                {k.key_preview} · scopes: {k.scopes.join(", ")}
              </p>
              <p className="mc-muted" style={{ fontSize: "0.8rem" }}>
                Créée: {ts(k.created_at)}
                {k.expires_at && ` · Expire: ${ts(k.expires_at)}`}
                {k.last_used_at && ` · Dernier usage: ${ts(k.last_used_at)}`}
              </p>
              {k.active && (
                <div className="mc-connector-actions">
                  <button
                    type="button"
                    className="mc-btn-sm mc-btn-danger"
                    onClick={() => handleRevoke(k.key_id)}
                  >
                    Révoquer
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="mc-card">
        <h2>{t('api_keys_cursor_usage')}</h2>
        <ol style={{ lineHeight: "2" }}>
          <li>Générez une clé avec scopes <code>read,write,mining</code></li>
          <li>Dans Cursor → Settings → API → Custom endpoint : <code>https://votre-ngrok.app/api/v1</code></li>
          <li>Header : <code>Authorization: Bearer artcb_…votre_token…</code></li>
          <li>Bob peut maintenant appeler la blockchain ARTCB directement depuis Cursor</li>
        </ol>
      </section>
    </div>
  );
}

