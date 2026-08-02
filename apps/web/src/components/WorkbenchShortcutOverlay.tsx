import { AlertTriangle, Command, Keyboard, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

export interface WorkbenchCommandAction {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
  readonly shortcut?: string;
  readonly keywords?: string;
  readonly disabled?: boolean;
  readonly run: () => void;
}

interface CommandPaletteProps {
  readonly actions: readonly WorkbenchCommandAction[];
  readonly initialQuery?: string;
  readonly onClose: () => void;
}

export function CommandPalette({ actions, initialQuery = "", onClose }: CommandPaletteProps) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const l = (en: string, zh: string) => english ? en : zh;
  const [query, setQuery] = useState(initialQuery);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return actions;
    return actions.filter((action) => `${action.label} ${action.detail} ${action.keywords ?? ""}`.toLowerCase().includes(normalized));
  }, [actions, query]);
  const run = (action: WorkbenchCommandAction) => {
    if (action.disabled) return;
    action.run();
    onClose();
  };
  return (
    <div className="shortcut-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section aria-label={l("Search commands and tools", "快速搜索功能和工具")} aria-modal="true" className="command-palette" role="dialog">
        <header>
          <Search aria-hidden="true" size={16} />
          <input
            aria-label={l("Search commands, drawing tools, or timeframes", "搜索功能、绘图工具或周期")}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") onClose();
              if (event.key === "Enter" && results[0] && !results[0].disabled) run(results[0]);
            }}
            placeholder={l("Search tools, timeframes, or actions…", "搜索工具、周期或操作…")}
            ref={inputRef}
            value={query}
          />
          <kbd>⌘/Ctrl K</kbd>
        </header>
        <div className="command-results">
          {results.map((action) => (
            <button disabled={action.disabled} key={action.id} onClick={() => run(action)} type="button">
              <span><strong>{action.label}</strong><small>{action.detail}</small></span>
              {action.shortcut && <kbd>{action.shortcut}</kbd>}
            </button>
          ))}
          {results.length === 0 && <p>{l(
            "No available action matches. A session cannot silently switch instruments or jump to a future date.",
            "没有匹配的可用操作。当前会话不能静默切换品种或跳到未来日期。",
          )}</p>}
        </div>
      </section>
    </div>
  );
}

interface ShortcutHelpProps {
  readonly onClose: () => void;
}

const GROUPS = [
  [["Drawing", "画线"], [
    [["Trend line", "趋势线"], "⌥/Alt + T"], [["Horizontal line", "水平线"], "⌥/Alt + H"], [["Vertical line", "垂直线"], "⌥/Alt + V"],
    [["Cross line", "十字线"], "⌥/Alt + C"], [["Fibonacci retracement", "斐波那契回撤"], "⌥/Alt + F"], [["Rectangle zone", "矩形区域"], "⌥/Alt + Shift + R"],
    [["Delete selected object", "删除选中对象"], "Delete / Backspace"], [["Copy / paste object", "复制 / 粘贴对象"], "⌘/Ctrl + C / V"],
  ]],
  [["Replay and chart", "回放与图表"], [
    [["Command search", "快速搜索"], "⌘/Ctrl + K"], [["Type a timeframe", "直接输入周期"], "1 / 5 / 15 / 60 / 240"], [["Play / pause", "播放 / 暂停"], "Space"],
    [["Advance 1 / 10 bars", "前进 1 / 10 根"], "→ / ⌘/Ctrl + →"], [["Chart zoom", "图表缩放"], "⌘/Ctrl + ↑ / ↓"], [["Reset chart", "复位图表"], "⌥/Alt + R"],
    [["Undo / redo drawing", "撤销 / 重做绘图"], "⌘/Ctrl + Z / Y"], [["Save chart layout locally", "保存本地图表布局"], "⌘/Ctrl + S"], [["Hide / show all drawings", "隐藏 / 显示全部绘图"], "⌘/Ctrl + ⌥/Alt + H"],
  ]],
  [["Paper-order drafts", "模拟交易草稿"], [
    [["Market buy / sell draft", "市价买入 / 卖出草稿"], "Shift + B / S"], [["Limit buy / sell draft", "限价买入 / 卖出草稿"], "Shift + ⌥/Alt + B / S"],
  ]],
] as const;

export function ShortcutHelp({ onClose }: ShortcutHelpProps) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const l = (en: string, zh: string) => english ? en : zh;
  return (
    <div className="shortcut-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section aria-labelledby="shortcut-help-title" aria-modal="true" className="shortcut-help" role="dialog">
        <header>
          <span><Keyboard aria-hidden="true" size={18} /><strong id="shortcut-help-title">{l("ReplayTutor keyboard shortcuts", "ReplayTutor 快捷键")}</strong></span>
          <button aria-label={l("Close keyboard shortcuts", "关闭快捷键说明")} onClick={onClose} type="button"><X aria-hidden="true" size={16} /></button>
        </header>
        <div className="shortcut-groups">
          {GROUPS.map(([labels, items]) => (
            <section key={labels[0]}>
              <h3>{english ? labels[0] : labels[1]}</h3>
              {items.map(([names, shortcut]) => <div key={names[0]}><span>{english ? names[0] : names[1]}</span><kbd>{shortcut}</kbd></div>)}
            </section>
          ))}
        </div>
        <div className="shortcut-safety-note">
          <AlertTriangle aria-hidden="true" size={17} />
          <p><strong>{l("Replay safety boundary", "回放安全边界")}</strong><span>{l(
            "Trading shortcuts only prepare a paper-order draft; they never submit it. Backward jumps, date seeking, and in-session instrument changes stay unbound to protect the revision, ledger, and visible_at boundary.",
            "交易键只预填模拟订单草稿，不会直接提交。向左回退、指定日期跳转和会话内换品种暂不绑定，避免破坏 revision、账本和 visible_at 反前视边界。",
          )}</span></p>
        </div>
        <footer><Command aria-hidden="true" size={14} /> {l("Press", "按")} <kbd>?</kbd> {l("to open this panel and", "随时打开此面板，按")} <kbd>Esc</kbd> {l("to close it.", "关闭。")}</footer>
      </section>
    </div>
  );
}
