import { useEffect, useState } from "react";
// B8 FIX: pas de setInterval — fetch unique au montage

interface GpuInfo {
  index: number;
  name: string;
  memory_mb?: number;
  driver?: string;
  backend: string;
}

interface SystemMetricsData {
  cpu: { percent: number; count: number; freq_mhz: number };
  memory: { total_gb: number; used_gb: number; available_gb: number; percent: number };
  disk: { total_gb: number; used_gb: number; free_gb: number; percent: number };
  network: { bytes_sent_mb: number; bytes_recv_mb: number; packets_sent: number; packets_recv: number };
  system: { system: string; release: string; hostname: string; processor: string };
  hardware?: {
    cpu: { logical_cores: number; physical_cores: number; freq_mhz: number };
    memory: { total_gb: number; available_gb: number };
    gpus: GpuInfo[];
    faiss_gpu_count: number;
  };
  optimization?: {
    agent_pool_workers: number;
    pool_chunk_chars: number;
    use_faiss: boolean;
    use_faiss_gpu: boolean;
    optimizations_active: string[];
  };
}

export function SystemMetrics() {
  const [metrics, setMetrics] = useState<SystemMetricsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch("/api/v1/metrics");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setMetrics(await res.json());
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return <p className="mc-error">Erreur metriques : {error}</p>;
  }

  if (!metrics) {
    return <p>Chargement metriques...</p>;
  }

  const bar = (pct: number) => (
    <div className="mc-hp-bar">
      <div
        className="mc-hp-fill"
        style={{
          width: `${pct}%`,
          background: pct < 50 ? "var(--mc-grass)" : pct < 75 ? "var(--mc-gold)" : "var(--mc-redstone)",
        }}
      />
    </div>
  );

  const hw = metrics.hardware;
  const opt = metrics.optimization;

  /* BUG-R8: chaque section reçoit un heading <h3> distinct pour la lisibilité */
  return (
    <div className="mc-f3-grid">
      <div className="mc-f3-section">
        <h3 className="mc-f3-heading">CPU</h3>
        <div>{metrics.cpu.count} cœurs · {metrics.cpu.percent.toFixed(1)}%</div>
        {bar(metrics.cpu.percent)}
        <div className="mc-muted">{metrics.cpu.freq_mhz.toFixed(0)} MHz</div>
        {hw && (
          <div className="mc-muted">
            {hw.cpu.physical_cores} physiques / {hw.cpu.logical_cores} logiques
          </div>
        )}
      </div>
      <div className="mc-f3-section">
        <h3 className="mc-f3-heading">RAM</h3>
        <div>{metrics.memory.percent.toFixed(1)}%</div>
        {bar(metrics.memory.percent)}
        <div className="mc-muted">
          {metrics.memory.used_gb.toFixed(1)} / {metrics.memory.total_gb.toFixed(1)} GB
        </div>
      </div>
      <div className="mc-f3-section">
        <h3 className="mc-f3-heading">Disque</h3>
        <div>{metrics.disk.percent.toFixed(1)}%</div>
        {bar(metrics.disk.percent)}
        <div className="mc-muted">{metrics.disk.free_gb.toFixed(1)} GB libre</div>
      </div>
      <div className="mc-f3-section">
        <h3 className="mc-f3-heading">Réseau</h3>
        <div>↑ {metrics.network.bytes_sent_mb.toFixed(1)} MB</div>
        <div>↓ {metrics.network.bytes_recv_mb.toFixed(1)} MB</div>
      </div>
      <div className="mc-f3-section">
        <h3 className="mc-f3-heading">Système</h3>
        <div><strong>{metrics.system.hostname}</strong></div>
        <div>{metrics.system.system} {metrics.system.release}</div>
        <div className="mc-muted">{metrics.system.processor}</div>
      </div>
      {hw && (
        <div>
          <div>
            <strong>GPU / FAISS</strong>
          </div>
          {hw.gpus.length === 0 ? (
            <div className="mc-muted">Aucun GPU CUDA detecte</div>
          ) : (
            hw.gpus.map((g) => (
              <div key={g.index} className="mc-muted">
                [{g.index}] {g.name} ({g.backend})
                {g.memory_mb != null ? ` - ${g.memory_mb} MB` : ""}
              </div>
            ))
          )}
          <div className="mc-muted">FAISS GPUs: {hw.faiss_gpu_count}</div>
        </div>
      )}
      {opt && (
        <div>
          <div>
            <strong>Optimisations</strong>
          </div>
          <div className="mc-muted">Workers: {opt.agent_pool_workers}</div>
          <div className="mc-muted">Chunk pool: {opt.pool_chunk_chars} chars</div>
          <div className="mc-muted">
            FAISS: {opt.use_faiss ? (opt.use_faiss_gpu ? "GPU" : "CPU") : "off"}
          </div>
          <div className="mc-muted">{opt.optimizations_active.join(", ")}</div>
        </div>
      )}
    </div>
  );
}
