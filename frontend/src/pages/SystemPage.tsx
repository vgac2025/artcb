import { SystemMetrics } from "../components/SystemMetrics";
import { useTranslation } from "../i18n/useTranslation";

export function SystemPage() {
  const { t } = useTranslation();
  return (
    <div className="mc-page">
      <h1 className="dashboard-title">{t('system_title')}</h1>
      <div className="mc-f3">
        <p className="mc-f3-title">{t('system_f3_title')}</p>
        <SystemMetrics />
      </div>
    </div>
  );
}
