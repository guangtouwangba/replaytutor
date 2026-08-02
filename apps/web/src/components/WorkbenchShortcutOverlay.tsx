import { AlertTriangle, Command, Keyboard, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

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
      <section aria-label="快速搜索功能和工具" aria-modal="true" className="command-palette" role="dialog">
        <header>
          <Search aria-hidden="true" size={16} />
          <input
            aria-label="搜索功能、绘图工具或周期"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") onClose();
              if (event.key === "Enter" && results[0] && !results[0].disabled) run(results[0]);
            }}
            placeholder="搜索工具、周期或操作…"
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
          {results.length === 0 && <p>没有匹配的可用操作。当前会话不能静默切换品种或跳到未来日期。</p>}
        </div>
      </section>
    </div>
  );
}

interface ShortcutHelpProps {
  readonly onClose: () => void;
}

const GROUPS = [
  ["画线", [
    ["趋势线", "⌥/Alt + T"], ["水平线", "⌥/Alt + H"], ["垂直线", "⌥/Alt + V"],
    ["十字线", "⌥/Alt + C"], ["斐波那契回撤", "⌥/Alt + F"], ["矩形区域", "⌥/Alt + Shift + R"],
    ["删除选中对象", "Delete / Backspace"], ["复制 / 粘贴对象", "⌘/Ctrl + C / V"],
  ]],
  ["回放与图表", [
    ["快速搜索", "⌘/Ctrl + K"], ["直接输入周期", "1 / 5 / 15 / 60 / 240"], ["播放 / 暂停", "Space"],
    ["前进 1 / 10 根", "→ / ⌘/Ctrl + →"], ["图表缩放", "⌘/Ctrl + ↑ / ↓"], ["复位图表", "⌥/Alt + R"],
    ["撤销 / 重做绘图", "⌘/Ctrl + Z / Y"], ["隐藏 / 显示全部绘图", "⌘/Ctrl + ⌥/Alt + H"],
  ]],
  ["模拟交易草稿", [
    ["市价买入 / 卖出草稿", "Shift + B / S"], ["限价买入 / 卖出草稿", "Shift + ⌥/Alt + B / S"],
  ]],
] as const;

export function ShortcutHelp({ onClose }: ShortcutHelpProps) {
  return (
    <div className="shortcut-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section aria-labelledby="shortcut-help-title" aria-modal="true" className="shortcut-help" role="dialog">
        <header>
          <span><Keyboard aria-hidden="true" size={18} /><strong id="shortcut-help-title">ReplayTutor 快捷键</strong></span>
          <button aria-label="关闭快捷键说明" onClick={onClose} type="button"><X aria-hidden="true" size={16} /></button>
        </header>
        <div className="shortcut-groups">
          {GROUPS.map(([label, items]) => (
            <section key={label}>
              <h3>{label}</h3>
              {items.map(([name, shortcut]) => <div key={name}><span>{name}</span><kbd>{shortcut}</kbd></div>)}
            </section>
          ))}
        </div>
        <div className="shortcut-safety-note">
          <AlertTriangle aria-hidden="true" size={17} />
          <p><strong>回放安全边界</strong><span>交易键只预填模拟订单草稿，不会直接提交。向左回退、指定日期跳转和会话内换品种暂不绑定，避免破坏 revision、账本和 visible_at 反前视边界。</span></p>
        </div>
        <footer><Command aria-hidden="true" size={14} /> 按 <kbd>?</kbd> 随时打开此面板，按 <kbd>Esc</kbd> 关闭。</footer>
      </section>
    </div>
  );
}
