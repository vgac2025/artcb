import { useEffect, useState } from "react";
import { useDashboard } from "../context/DashboardContext";
import { useTranslation } from "../i18n/useTranslation";
import {
  addP2PPeer,
  createPoolJob,
  fetchNotificationChannels,
  fetchPoolJobs,
  fetchPoolStatus,
  fetchP2PStatus,
  fetchP2PPeers,
  finalizePoolJob,
  processAllPoolIncoming,
  saveNotificationChannel,
  syncP2PAll,
} from "../api/client";

export function Network() {
  const { t } = useTranslation();
  const { visibility, groupId, useDistributedPool, setUseDistributedPool, encryptTransport } = useDashboard();
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [peers, setPeers] = useState<Array<Record<string, unknown>>>([]);
  const [channels, setChannels] = useState<Array<Record<string, unknown>>>([]);
  /* BUG-R4: champs vides par défaut — évite duplication quand l'utilisateur tape */
  const [host, setHost] = useState("");
  const [port, setPort] = useState("");
  const [peerKem, setPeerKem] = useState("");
  const [notifLabel, setNotifLabel] = useState("");
  const [notifSecret, setNotifSecret] = useState("");
  const [chatId, setChatId] = useState("");
  const [poolText, setPoolText] = useState(
    "Texte long pour pool E2E : segment A local, segment B distant — transport ML-KEM chiffré.",
  );
  const [poolWallet, setPoolWallet] = useState("");
  const [poolStatus, setPoolStatus] = useState<Record<string, unknown> | null>(null);
  const [poolJobs, setPoolJobs] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const reload = async () => {
    setStatus(await fetchP2PStatus());
    setPeers((await fetchP2PPeers()).peers);
    setChannels((await fetchNotificationChannels()).channels);
    setPoolStatus(await fetchPoolStatus());
    setPoolJobs((await fetchPoolJobs()).jobs);
  };

  useEffect(() => {
    reload().catch((e) => setError(String(e)));
  }, []);

  const handleAddPeer = async () => {
    try {
      await addP2PPeer({ host, port: parseInt(port, 10), kem_public_key_hex: peerKem, label: `${host}:${port}` });
      setSuccess("Pair P2P ajouté");
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSync = async () => {
    try {
      const r = await syncP2PAll();
      setSuccess(`Sync terminée — ${r.peer_count} pair(s)`);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSaveNotif = async () => {
    try {
      await saveNotificationChannel({
        channel_type: "telegram",
        label: notifLabel || "Telegram",
        secret: notifSecret,
        config: { chat_id: chatId },
      });
      setSuccess("Canal Telegram enregistré (local chiffré)");
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleCreatePoolJob = async () => {
    try {
      const r = await createPoolJob({
        text: poolText,
        visibility,
        group_id: visibility === "group" ? groupId ?? undefined : undefined,
        wallet_name: poolWallet || undefined,
        auto_dispatch: true,
        chunk_chars: 120,
        encrypt_transport: true,
      });
      setSuccess(`Job pool créé (${String(r.job.job_id)}) — transport chiffré ML-KEM`);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleProcessPoolIncoming = async () => {
    try {
      const r = await processAllPoolIncoming({ wallet_name: poolWallet || undefined });
      setSuccess(`Chunks pool traités localement : ${r.count}`);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleFinalizeLatestPool = async () => {
    try {
      const ready = poolJobs.find((j) => j.status === "ready_finalize");
      if (!ready) {
        setError("Aucun job ready_finalize");
        return;
      }
      await finalizePoolJob(String(ready.job_id), poolText);
      setSuccess(`Job ${String(ready.job_id)} finalisé avec contributors pool_worker`);
      await reload();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('nav_network')}</h1>
      <p className="mc-hint">
        <strong>Calcul local par défaut</strong> — le <strong>pool opt-in</strong> distribue des morceaux
        chiffrés <strong>ML-KEM-768</strong> (contextes <code>artcb-pool-chunk-v1</code> / <code>artcb-pool-result-v1</code>).
        Chaque worker déchiffre et raisonne <strong>localement</strong> — jamais de texte en clair sur le réseau.
        Sync P2P classique = blocs <strong>publics</strong> uniquement.
      </p>
      {error && <p className="mc-error">{error}</p>}
      {success && <p className="mc-success">{success}</p>}

      {status && (
        <section className="mc-card">
          <h2>Nœud local</h2>
          <p>Network: {String(status.network_id)} · Node: {String(status.node_id)}</p>
          <p>ML-KEM pub: {String(status.kem_public_key_hex).slice(0, 32)}…</p>
          <p>Blocs publics locaux: {String(status.public_blocks_local)} · reçus P2P: {String(status.public_blocks_incoming)}</p>
          <button type="button" className="mc-btn" onClick={handleSync}>Synchroniser tous les pairs</button>
        </section>
      )}

      <section className="mc-card">
        <h2>Ajouter un pair</h2>
        <label>Host<input value={host} onChange={(e) => setHost(e.target.value)} /></label>
        <label>Port API<input value={port} onChange={(e) => setPort(e.target.value)} /></label>
        <label>Clé publique ML-KEM du pair (hex)<textarea value={peerKem} onChange={(e) => setPeerKem(e.target.value)} rows={2} /></label>
        {/* B4 FIX: message d'erreur explicite quand ML-KEM trop courte */}
        {peerKem.length > 0 && peerKem.length < 32 && (
          <p className="mc-error" style={{ margin: "4px 0", fontSize: "0.85rem" }}>
            La clé ML-KEM doit contenir au moins 32 caractères ({peerKem.length}/32)
          </p>
        )}
        <button type="button" className="mc-btn" onClick={handleAddPeer} disabled={peerKem.length < 32}>Ajouter</button>
      </section>

      <section className="mc-card">
        <h2>Pairs ({peers.length})</h2>
        <ul className="mc-connector-list">
          {peers.map((p) => (
            <li key={String(p.peer_id)} className="mc-connector-item">
              {String(p.label || p.peer_id)} — {String(p.base_url)}
              {p.last_sync_ok != null && <span> · sync {p.last_sync_ok ? "OK" : "X"}</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="mc-card">
        <h2>Pool calcul distribué (E2E ML-KEM)</h2>
        {poolStatus && (
          <p>
            Crypto: {String(poolStatus.crypto)} · Jobs: {String(poolStatus.job_count)} ·
            Incoming: {String(poolStatus.incoming_pending)} · Réseau clair:{" "}
            {poolStatus.plaintext_on_network ? "oui" : "non"}
          </p>
        )}
        <label>
          Texte à distribuer (découpé en chunks chiffrés)
          <textarea value={poolText} onChange={(e) => setPoolText(e.target.value)} rows={3} />
        </label>
        <label>
          <input
            type="checkbox"
            checked={useDistributedPool}
            onChange={(e) => setUseDistributedPool(e.target.checked)}
          />{" "}
          Activer calcul distribué par défaut (préférence UI)
        </label>
        <p className="mc-muted">
          Visibilité : <strong>{visibility}</strong>
          {visibility === "group" && groupId ? ` · groupe ${groupId.slice(0, 12)}…` : ""}
          · Chiffrement pool : <strong>{encryptTransport ? "ML-KEM obligatoire" : "—"}</strong>
        </p>
        <label>
          Wallet (optionnel)
          <input value={poolWallet} onChange={(e) => setPoolWallet(e.target.value)} placeholder="mon_wallet" />
        </label>
        <button type="button" className="mc-btn" onClick={handleCreatePoolJob} disabled={poolText.length < 20}>
          Créer job pool + dispatch
        </button>
        <button type="button" className="mc-btn" onClick={handleProcessPoolIncoming}>
          Traiter chunks incoming (worker)
        </button>
        <button type="button" className="mc-btn" onClick={handleFinalizeLatestPool}>
          Finalize job (owner)
        </button>
        <p>Jobs: {poolJobs.length}</p>
      </section>

      <section className="mc-card">
        <h2>Alertes Telegram</h2>
        <p className="mc-hint">
          Notifications à chaque bloc gravé. Créez un bot via @BotFather, récupérez le token et votre chat_id.
          Gmail retiré — OAuth Google trop complexe pour cette release.
        </p>
        <label>Nom<input value={notifLabel} onChange={(e) => setNotifLabel(e.target.value)} placeholder="Mon bot ARTCB" /></label>
        <label>Chat ID<input value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="123456789" /></label>
        <label>
          Bot token
          <input type="password" value={notifSecret} onChange={(e) => setNotifSecret(e.target.value)} />
        </label>
        <button type="button" className="mc-btn" onClick={handleSaveNotif} disabled={notifSecret.length < 8 || !chatId}>Enregistrer</button>
        <p>Canaux actifs: {channels.length}</p>
      </section>
    </div>
  );
}
