import { useEffect, useState } from "react";
import { fetchDemoLiveLog, fetchRtlegEvents } from "../api/client";
import { useTranslation } from "../i18n/useTranslation";

export function Logs() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<
    Array<{
      event_id: string;
      timestamp: string;
      agent: string;
      event_type: string;
      session_id: string;
    }>
  >([]);
  const [demoLines, setDemoLines] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRtlegEvents()
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : "RT-LEG erreur"));
    fetchDemoLiveLog()
      .then((d) => setDemoLines(d.lines))
      .catch((e) => setError((prev) => prev ?? (e instanceof Error ? e.message : "demo_live erreur")));
  }, []);

  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('logs_title')}</h1>

      <div className="panel mc-chat-log">
        <h2>{t('logs_demo_title')}</h2>
        {demoLines.length === 0 && <p className="mc-muted">{t('logs_demo_loading')}</p>}
        <pre className="mc-pre">{demoLines.join("\n")}</pre>
      </div>

      <div className="panel mc-chat-log">
        <h2>{t('logs_rtleg_title')}</h2>
        {error && <p className="mc-error">{error}</p>}
        <ul className="mc-chat-list">
          {[...events].reverse().map((ev) => (
            <li key={ev.event_id}>
              <span className="mc-chat-ts">[{ev.timestamp}]</span>{" "}
              <span className="mc-chat-event">{ev.agent}</span> <span>{ev.event_type}</span>
              <span className="mc-muted"> · {ev.session_id}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
