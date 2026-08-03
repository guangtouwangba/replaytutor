import { Bot, Eye, EyeOff, Plus, Search, Settings2, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createIndicatorInstance,
  indicatorDefinition,
  searchIndicators,
  type IndicatorCategory,
  type IndicatorInstance,
  supportsTutorEvidence,
} from "../chart/IndicatorCatalog";

interface IndicatorPanelProps {
  readonly open: boolean;
  readonly paneNumber: number;
  readonly instances: readonly IndicatorInstance[];
  readonly onChange: (instances: IndicatorInstance[]) => void;
  readonly onApplyAll: (instances: IndicatorInstance[]) => void;
  readonly contextInstanceIds?: readonly string[];
  readonly onToggleContext?: (instanceId: string) => void;
  readonly onClose: () => void;
}

const categoryLabels: Record<IndicatorCategory, { en: string; zh: string }> = {
  trend: { en: "Trend", zh: "趋势" },
  momentum: { en: "Momentum", zh: "动量" },
  volatility: { en: "Volatility", zh: "波动" },
  volume: { en: "Volume", zh: "成交量" },
  structure: { en: "Structure", zh: "结构" },
};

function parseParams(value: string): number[] | null {
  if (!value.trim()) return [];
  const values = value.split(",").map((item) => Number(item.trim()));
  return values.length <= 8 && values.every((item) => Number.isFinite(item) && item > 0) ? values : null;
}

export function IndicatorPanel({
  open,
  paneNumber,
  instances,
  onChange,
  onApplyAll,
  contextInstanceIds = [],
  onToggleContext,
  onClose,
}: IndicatorPanelProps) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [parameterDraft, setParameterDraft] = useState("");
  const [parameterError, setParameterError] = useState(false);
  const matches = useMemo(() => searchIndicators(query), [query]);
  if (!open) return null;

  const l = (en: string, zh: string) => english ? en : zh;
  const replace = (next: IndicatorInstance) => onChange(
    instances.map((item) => item.instanceId === next.instanceId ? next : item),
  );

  return (
    <section aria-label={l("Indicators", "指标")} className="indicator-panel">
      <header>
        <div>
          <strong>{l("Indicators", "指标")}</strong>
          <small>{l(`Chart ${paneNumber}`, `窗口 ${paneNumber}`)}</small>
        </div>
        <button aria-label={l("Close indicators", "关闭指标")} onClick={onClose} type="button"><X size={15} /></button>
      </header>

      <div className="indicator-search">
        <Search aria-hidden="true" size={14} />
        <input
          autoFocus
          onChange={(event) => setQuery(event.target.value)}
          placeholder={l("Search MA, EMA, volume, OB…", "搜索 MA、EMA、成交量、OB…")}
          value={query}
        />
      </div>

      <div className="indicator-current">
        <div className="indicator-section-title">
          <span>{l("Current chart", "当前窗口")}</span>
          {instances.length > 0 && (
            <button onClick={() => onApplyAll([...instances])} type="button">
              {l("Apply to all charts", "应用到全部窗口")}
            </button>
          )}
        </div>
        {instances.length === 0 && <p>{l("No indicators added.", "尚未添加指标。")}</p>}
        {instances.map((instance) => {
          const item = indicatorDefinition(instance.definitionId);
          const editing = editingId === instance.instanceId;
          return (
            <div className="indicator-instance" key={instance.instanceId}>
              <button
                aria-label={instance.visible ? l("Hide indicator", "隐藏指标") : l("Show indicator", "显示指标")}
                onClick={() => replace({ ...instance, visible: !instance.visible })}
                type="button"
              >
                {instance.visible ? <Eye size={13} /> : <EyeOff size={13} />}
              </button>
              <span><strong>{item.id}</strong><small>{english ? item.label : item.labelZh}</small></span>
              {supportsTutorEvidence(item.id) ? (
                <button
                  aria-label={contextInstanceIds.includes(instance.instanceId) ? l("Remove from Tutor context", "移出 Tutor 上下文") : l("Add to Tutor context", "加入 Tutor 上下文")}
                  className={contextInstanceIds.includes(instance.instanceId) ? "is-context" : ""}
                  onClick={() => onToggleContext?.(instance.instanceId)}
                  title={l("Use server-calculated values in the next Tutor question", "下一轮 Tutor 使用服务端计算的指标证据")}
                  type="button"
                ><Bot size={13} /></button>
              ) : <span aria-hidden="true" />}
              <button
                aria-label={l("Indicator settings", "指标参数")}
                onClick={() => {
                  setEditingId(editing ? null : instance.instanceId);
                  setParameterDraft((instance.params ?? item.defaultParams ?? []).join(", "));
                  setParameterError(false);
                }}
                type="button"
              ><Settings2 size={13} /></button>
              <button
                aria-label={l("Remove indicator", "删除指标")}
                onClick={() => onChange(instances.filter((candidate) => candidate.instanceId !== instance.instanceId))}
                type="button"
              ><Trash2 size={13} /></button>
              {editing && (
                <form
                  className="indicator-params"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const params = parseParams(parameterDraft);
                    if (params === null) {
                      setParameterError(true);
                      return;
                    }
                    replace({ ...instance, params: params.length > 0 ? params : undefined });
                    setEditingId(null);
                    setParameterError(false);
                  }}
                >
                  <label>
                    {l("Parameters, comma separated", "参数，用逗号分隔")}
                    <input onChange={(event) => setParameterDraft(event.target.value)} value={parameterDraft} />
                  </label>
                  <button type="submit">{l("Apply", "应用")}</button>
                  {parameterError && <small role="alert">{l("Use up to 8 positive numbers.", "最多输入 8 个正数。")}</small>}
                </form>
              )}
            </div>
          );
        })}
      </div>

      <div className="indicator-catalog">
        {matches.map((item) => (
          <button
            aria-label={l(`Add ${item.id}`, `添加 ${item.id}`)}
            className="indicator-catalog-item"
            key={item.id}
            onClick={() => onChange([...instances, createIndicatorInstance(item.id)])}
            type="button"
          >
            <span><strong>{item.id}</strong><small>{english ? item.label : item.labelZh}</small></span>
            <em>{english ? categoryLabels[item.category].en : categoryLabels[item.category].zh} · {item.placement === "main" ? l("Overlay", "主图") : l("Pane", "副图")}</em>
            <Plus aria-hidden="true" size={14} />
          </button>
        ))}
      </div>
    </section>
  );
}
