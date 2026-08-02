import type { LocalPreferences } from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArchiveRestore, DatabaseBackup, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchHealth } from "../api/health";
import {
  cleanupAgentRuns,
  createBackup,
  fetchMaintenance,
  fetchPreferences,
  restoreBackup,
  savePreferences,
} from "../api/localSystem";
import { discoverCodex } from "../api/tutor";
import { applyLocale, type LocalePreference } from "../i18n";

export function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health-detail"], queryFn: () => fetchHealth() });
  const codex = useQuery({ queryKey: ["codex-capability"], queryFn: discoverCodex });
  const preferences = useQuery({ queryKey: ["local-preferences"], queryFn: fetchPreferences });
  const maintenance = useQuery({ queryKey: ["maintenance"], queryFn: fetchMaintenance });
  const [draft, setDraft] = useState<LocalPreferences | null>(null);
  useEffect(() => {
    if (preferences.data) setDraft(preferences.data);
  }, [preferences.data]);
  const save = useMutation({
    mutationFn: savePreferences,
    onSuccess: (value) => {
      queryClient.setQueryData(["local-preferences"], value);
      setDraft(value);
      void applyLocale(value.locale ?? "system");
    },
  });
  const backup = useMutation({
    mutationFn: createBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });
  const restore = useMutation({
    mutationFn: restoreBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });
  const cleanup = useMutation({
    mutationFn: cleanupAgentRuns,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });

  return (
    <section className="page settings-page">
      <div className="page-kicker">{t("settings.kicker")}</div>
      <h1>{t("settings.title")}</h1>
      <div className="settings-grid">
        <article><ShieldCheck size={20} /><h2>Codex Tutor</h2><dl><div><dt>{t("settings.executable")}</dt><dd>{codex.data?.executable ?? t("settings.notFound")}</dd></div><div><dt>{t("settings.version")}</dt><dd>{codex.data?.version ?? "—"}</dd></div><div><dt>{t("settings.status")}</dt><dd>{codex.data?.available ? t("settings.available") : t("settings.unavailable")}</dd></div><div><dt>{t("settings.permissions")}</dt><dd>read-only · ephemeral</dd></div></dl></article>
        <article><h2>{t("settings.system")}</h2><dl><div><dt>{t("settings.database")}</dt><dd>{health.data?.database.status ?? "…"}</dd></div><div><dt>{t("settings.migration")}</dt><dd>{health.data?.database.migration_current ?? "—"}</dd></div><div><dt>{t("settings.dataDir")}</dt><dd>{health.data?.data.path ?? "—"}</dd></div><div><dt>{t("settings.binding")}</dt><dd>127.0.0.1</dd></div></dl></article>
      </div>
      {draft && (
        <form className="settings-form" onSubmit={(event) => { event.preventDefault(); save.mutate(draft); }}>
          <div><div className="page-kicker">{t("settings.training")}</div><h2>{t("settings.trainingPrivacy")}</h2></div>
          <label>{t("settings.language")}<select onChange={(event) => { const locale = event.target.value as LocalePreference; setDraft({ ...draft, locale }); void applyLocale(locale); }} value={draft.locale ?? "system"}><option value="system">{t("settings.systemLanguage")}</option><option value="en-US">{t("settings.english")}</option><option value="zh-CN">{t("settings.chinese")}</option></select></label>
          <label>{t("settings.aiMode")}<select onChange={(event) => setDraft({ ...draft, ai_mode: event.target.value as "codex" | "off" })} value={draft.ai_mode}><option value="codex">Codex Tutor</option><option value="off">{t("settings.aiOff")}</option></select></label>
          <label>{t("settings.retention")}<input min="1" max="365" onChange={(event) => setDraft({ ...draft, retain_agent_runs_days: Number(event.target.value) })} type="number" value={draft.retain_agent_runs_days} /></label>
          <label className="check-row"><input checked={draft.confirm_before_finish} onChange={(event) => setDraft({ ...draft, confirm_before_finish: event.target.checked })} type="checkbox" /><span><strong>{t("settings.confirm")}</strong><small>{t("settings.savedLocal")}</small></span></label>
          <div className="inline-notice">{t("settings.privacy")}</div>
          <button className="primary-action" disabled={save.isPending} type="submit">{t("settings.save")}</button>
        </form>
      )}
      <section className="maintenance-panel">
        <div className="review-section-heading"><div><div className="page-kicker">{t("settings.maintenance")}</div><h2>{t("settings.backupCleanup")}</h2></div><button className="secondary-action" disabled={backup.isPending} onClick={() => backup.mutate()} type="button"><DatabaseBackup size={14} />{t("settings.createBackup")}</button></div>
        <p>{t("settings.recoveryNote")}</p>
        <div className="backup-list">
          {maintenance.data?.backups.map((item) => (
            <div key={item.backup_id}><code>{item.backup_id}</code><span>{(item.size_bytes / 1024).toFixed(1)} KB · {item.sha256.slice(0, 10)}</span><button disabled={restore.isPending} onClick={() => { if (window.confirm(t("settings.restoreConfirm"))) restore.mutate(item.backup_id); }} type="button"><ArchiveRestore size={13} />{t("settings.restore")}</button></div>
          ))}
          {!maintenance.isLoading && maintenance.data?.backups.length === 0 && <div className="panel-empty">{t("settings.noBackups")}</div>}
        </div>
        <button className="secondary-action" disabled={cleanup.isPending} onClick={() => cleanup.mutate()} type="button"><Trash2 size={13} />{t("settings.cleanup")}</button>
        {cleanup.data && <small>{t("settings.cleaned", { count: cleanup.data.moved_agent_runs })}</small>}
      </section>
      <div className="inline-notice">{t("settings.aiBoundary")}</div>
    </section>
  );
}
