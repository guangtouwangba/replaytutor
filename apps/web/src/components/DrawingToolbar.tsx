import {
  ArrowDownFromLine,
  ArrowRight,
  ArrowUpFromLine,
  BadgeDollarSign,
  ChevronRight,
  CircleMinus,
  CirclePlus,
  Eye,
  EyeOff,
  GitBranch,
  List,
  Lock,
  LogIn,
  LogOut,
  Magnet,
  MessageSquarePlus,
  Minus,
  MoveDiagonal2,
  MoveUpRight,
  MoveVertical,
  MousePointer2,
  Ratio,
  Redo2,
  Repeat2,
  Ruler,
  ShieldAlert,
  Square,
  Target,
  Trash2,
  TrendingUp,
  Type,
  Undo2,
  Unlock,
  type LucideIcon,
} from "lucide-react";
import { type FocusEvent, type MouseEvent, useEffect, useRef, useState } from "react";
import {
  DRAWING_DEFINITIONS,
  ADVANCED_TOOL_IDS,
  ADVANCED_TOOL_SECTIONS,
  LINE_TOOL_IDS,
  LINE_TOOL_SECTIONS,
  drawingDefinition,
  type DrawingGroup,
  type DrawingTool,
} from "../chart/DrawingController";
import { DRAWING_SHORTCUT_LABELS } from "../chart/WorkbenchShortcuts";

interface DrawingToolbarProps {
  readonly activeTool: DrawingTool;
  readonly disabled: boolean;
  readonly magnetEnabled: boolean;
  readonly continuousDrawing: boolean;
  readonly annotationsVisible: boolean;
  readonly annotationsLocked: boolean;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly historyPending: boolean;
  readonly canDelete: boolean;
  readonly onSelect: (tool: DrawingTool) => void;
  readonly onToggleMagnet: () => void;
  readonly onToggleContinuous: () => void;
  readonly onToggleAnnotations: () => void;
  readonly onToggleLock: () => void;
  readonly onDelete: () => void;
  readonly onUndo: () => void;
  readonly onRedo: () => void;
}

const TOOL_ICONS: Record<DrawingTool, LucideIcon> = {
  select: MousePointer2,
  trend_line: TrendingUp,
  trend_ray: MoveUpRight,
  extended_line: MoveDiagonal2,
  price_line: BadgeDollarSign,
  horizontal_ray: ArrowRight,
  vertical_line: MoveVertical,
  parallel_channel: GitBranch,
  price_channel: List,
  fibonacci_retracement: List,
  measure: Ruler,
  horizontal_line: Minus,
  zone: Square,
  text: Type,
  note_marker: MessageSquarePlus,
  planned_entry: LogIn,
  add_position: CirclePlus,
  reduce_position: CircleMinus,
  planned_exit: LogOut,
  stop_loss: ShieldAlert,
  take_profit: Target,
  long_position: ArrowUpFromLine,
  short_position: ArrowDownFromLine,
  risk_reward: Ratio,
  info_line: Ruler,
  trend_angle: MoveUpRight,
  cross_line: CirclePlus,
  regression_trend: TrendingUp,
  flat_top_bottom: List,
  disjoint_channel: GitBranch,
  anchored_vwap: BadgeDollarSign,
  fibonacci_extension: List,
  fibonacci_channel: GitBranch,
  fibonacci_time_zone: MoveVertical,
  pitchfork: GitBranch,
  price_range: MoveVertical,
  date_range: ArrowRight,
  brush: MessageSquarePlus,
  polyline: GitBranch,
  head_shoulders: TrendingUp,
  triangle_pattern: MoveUpRight,
};

export function DrawingToolbar({
  activeTool,
  disabled,
  magnetEnabled,
  continuousDrawing,
  annotationsVisible,
  annotationsLocked,
  canUndo,
  canRedo,
  historyPending,
  canDelete,
  onSelect,
  onToggleMagnet,
  onToggleContinuous,
  onToggleAnnotations,
  onToggleLock,
  onDelete,
  onUndo,
  onRedo,
}: DrawingToolbarProps) {
  const lineLauncherRef = useRef<HTMLButtonElement>(null);
  const linePanelRef = useRef<HTMLDivElement>(null);
  const advancedLauncherRef = useRef<HTMLButtonElement>(null);
  const advancedPanelRef = useRef<HTMLDivElement>(null);
  const [lineMenuOpen, setLineMenuOpen] = useState(false);
  const [advancedMenuOpen, setAdvancedMenuOpen] = useState(false);
  const [lineMenuPosition, setLineMenuPosition] = useState({ left: 0, top: 0 });
  const [lastLineTool, setLastLineTool] = useState<Exclude<DrawingTool, "select">>("trend_line");
  const [lastAdvancedTool, setLastAdvancedTool] = useState<Exclude<DrawingTool, "select">>("fibonacci_retracement");
  const [tooltip, setTooltip] = useState<{
    label: string;
    detail?: string;
    left: number;
    top: number;
  } | null>(null);
  useEffect(() => {
    if (LINE_TOOL_IDS.some((tool) => tool === activeTool)) {
      setLastLineTool(activeTool as Exclude<DrawingTool, "select">);
    }
  }, [activeTool]);
  useEffect(() => {
    if (ADVANCED_TOOL_IDS.some((tool) => tool === activeTool)) {
      setLastAdvancedTool(activeTool as Exclude<DrawingTool, "select">);
    }
  }, [activeTool]);
  useEffect(() => {
    if (!lineMenuOpen) return;
    const close = (event: PointerEvent) => {
      const target = event.target as Node;
      if (lineLauncherRef.current?.contains(target) || linePanelRef.current?.contains(target)) return;
      setLineMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setLineMenuOpen(false);
    };
    window.addEventListener("pointerdown", close);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [lineMenuOpen]);
  useEffect(() => {
    if (!advancedMenuOpen) return;
    const close = (event: PointerEvent) => {
      const target = event.target as Node;
      if (advancedLauncherRef.current?.contains(target) || advancedPanelRef.current?.contains(target)) return;
      setAdvancedMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAdvancedMenuOpen(false);
    };
    window.addEventListener("pointerdown", close);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [advancedMenuOpen]);
  const tooltipProps = (label: string, detail?: string) => ({
    "aria-describedby": "drawing-tool-tooltip",
    onMouseEnter: (event: MouseEvent<HTMLButtonElement>) => {
      const bounds = event.currentTarget.getBoundingClientRect();
      setTooltip({
        label,
        detail,
        left: bounds.right + 8,
        top: Math.min(bounds.top + bounds.height / 2, window.innerHeight - 48),
      });
    },
    onMouseLeave: () => setTooltip(null),
    onFocus: (event: FocusEvent<HTMLButtonElement>) => {
      const bounds = event.currentTarget.getBoundingClientRect();
      setTooltip({
        label,
        detail,
        left: bounds.right + 8,
        top: Math.min(bounds.top + bounds.height / 2, window.innerHeight - 48),
      });
    },
    onBlur: () => setTooltip(null),
  });
  const openLineMenu = () => {
    const bounds = lineLauncherRef.current?.getBoundingClientRect();
    if (bounds) {
      setLineMenuPosition({
        left: bounds.right + 8,
        top: Math.max(8, Math.min(bounds.top, window.innerHeight - 500)),
      });
    }
    setTooltip(null);
    setAdvancedMenuOpen(false);
    setLineMenuOpen((value) => !value);
  };
  const selectLineTool = (tool: Exclude<DrawingTool, "select">) => {
    setLastLineTool(tool);
    setLineMenuOpen(false);
    onSelect(tool);
  };
  const activeLineTool = LINE_TOOL_IDS.some((tool) => tool === activeTool);
  const activeAdvancedTool = ADVANCED_TOOL_IDS.some((tool) => tool === activeTool);
  const LineLauncherIcon = TOOL_ICONS[lastLineTool];
  const AdvancedLauncherIcon = TOOL_ICONS[lastAdvancedTool];
  let previousGroup: DrawingGroup | null = "analysis";
  return (
    <>
      <aside className="drawing-rail" aria-label="图表绘图工具">
      <button
        {...tooltipProps("选择工具", "选择、移动或检查图表对象")}
        aria-label="选择工具"
        aria-pressed={activeTool === "select"}
        className={activeTool === "select" ? "is-active" : ""}
        disabled={disabled}
        onClick={() => onSelect("select")}
        title="选择工具"
        type="button"
      >
        <MousePointer2 aria-hidden="true" size={19} strokeWidth={1.7} />
      </button>
      <button
        {...tooltipProps("线类工具", `${drawingDefinition(lastLineTool).label}及扩展线工具`)}
        aria-controls="line-tool-panel"
        aria-expanded={lineMenuOpen}
        aria-haspopup="menu"
        aria-label="线类工具"
        aria-pressed={activeLineTool}
        className={`${activeLineTool ? "is-active" : ""} tool-group-start grouped-tool`}
        disabled={disabled}
        onClick={openLineMenu}
        ref={lineLauncherRef}
        title={drawingDefinition(lastLineTool).label}
        type="button"
      >
        <LineLauncherIcon aria-hidden="true" size={19} strokeWidth={1.7} />
        <ChevronRight aria-hidden="true" className="grouped-tool-chevron" size={10} strokeWidth={1.8} />
      </button>
      <button
        {...tooltipProps("分析工具", `${drawingDefinition(lastAdvancedTool).label}及扩展分析工具`)}
        aria-controls="advanced-tool-panel"
        aria-expanded={advancedMenuOpen}
        aria-haspopup="menu"
        aria-label="分析工具"
        aria-pressed={activeAdvancedTool}
        className={`${activeAdvancedTool ? "is-active" : ""} grouped-tool`}
        disabled={disabled}
        onClick={() => {
          const bounds = advancedLauncherRef.current?.getBoundingClientRect();
          if (bounds) setLineMenuPosition({ left: bounds.right + 8, top: Math.max(8, Math.min(bounds.top, window.innerHeight - 560)) });
          setLineMenuOpen(false);
          setAdvancedMenuOpen((value) => !value);
        }}
        ref={advancedLauncherRef}
        title={drawingDefinition(lastAdvancedTool).label}
        type="button"
      >
        <AdvancedLauncherIcon aria-hidden="true" size={19} strokeWidth={1.7} />
        <ChevronRight aria-hidden="true" className="grouped-tool-chevron" size={10} strokeWidth={1.8} />
      </button>
      {DRAWING_DEFINITIONS.filter((definition) => (
        !LINE_TOOL_IDS.some((tool) => tool === definition.tool)
        && !ADVANCED_TOOL_IDS.some((tool) => tool === definition.tool)
      )).map((definition) => {
        const Icon = TOOL_ICONS[definition.tool];
        const startsGroup = previousGroup !== definition.group;
        previousGroup = definition.group;
        return (
          <button
            {...tooltipProps(definition.label, `${definition.instruction}${DRAWING_SHORTCUT_LABELS[definition.tool] ? ` · ${DRAWING_SHORTCUT_LABELS[definition.tool]}` : ""}`)}
            aria-label={definition.label}
            aria-pressed={activeTool === definition.tool}
            className={`${activeTool === definition.tool ? "is-active" : ""} ${startsGroup ? "tool-group-start" : ""}`}
            disabled={disabled}
            key={definition.tool}
            onClick={() => onSelect(definition.tool)}
            title={`${definition.label}${DRAWING_SHORTCUT_LABELS[definition.tool] ? ` · ${DRAWING_SHORTCUT_LABELS[definition.tool]}` : ""}`}
            type="button"
          >
            <Icon aria-hidden="true" size={19} strokeWidth={1.7} />
          </button>
        );
      })}
      <div className="drawing-rail-spacer" />
      <button
        {...tooltipProps("撤销", "撤销上一次图表对象操作")}
        aria-label="撤销上一次图表对象操作"
        className="utility-tool"
        disabled={!canUndo || historyPending || disabled}
        onClick={onUndo}
        title="撤销"
        type="button"
      >
        <Undo2 aria-hidden="true" size={19} strokeWidth={1.7} />
      </button>
      <button
        {...tooltipProps("重做", "恢复上一次撤销的图表对象操作")}
        aria-label="重做上一次图表对象操作"
        className="utility-tool"
        disabled={!canRedo || historyPending || disabled}
        onClick={onRedo}
        title="重做"
        type="button"
      >
        <Redo2 aria-hidden="true" size={19} strokeWidth={1.7} />
      </button>
      <button
        {...tooltipProps(continuousDrawing ? "关闭连续绘制" : "开启连续绘制", "完成一个对象后继续使用当前工具")}
        aria-label={continuousDrawing ? "关闭连续绘制" : "开启连续绘制"}
        aria-pressed={continuousDrawing}
        className={continuousDrawing ? "is-active utility-tool" : "utility-tool"}
        disabled={disabled}
        onClick={onToggleContinuous}
        title={continuousDrawing ? "连续绘制已开启" : "开启连续绘制"}
        type="button"
      >
        <Repeat2 aria-hidden="true" size={19} strokeWidth={1.7} />
      </button>
      <button
        {...tooltipProps(
          magnetEnabled ? "关闭磁吸" : "开启磁吸",
          "吸附到最近可见 K 线的 OHLC",
        )}
        aria-label={magnetEnabled ? "关闭磁吸" : "开启磁吸"}
        aria-pressed={magnetEnabled}
        className={magnetEnabled ? "is-active utility-tool" : "utility-tool"}
        disabled={disabled}
        onClick={onToggleMagnet}
        title={magnetEnabled ? "磁吸已开启：吸附到最近 K 线的 OHLC" : "开启磁吸"}
        type="button"
      >
        <Magnet aria-hidden="true" size={19} strokeWidth={1.7} />
      </button>
      <button
        {...tooltipProps(
          annotationsVisible ? "隐藏图表对象" : "显示图表对象",
          "切换用户和 AI 图层的可见性",
        )}
        aria-label={annotationsVisible ? "隐藏全部图表对象" : "显示全部图表对象"}
        aria-pressed={annotationsVisible}
        className={annotationsVisible ? "utility-tool is-active" : "utility-tool"}
        onClick={onToggleAnnotations}
        title={annotationsVisible ? "隐藏全部图表对象" : "显示全部图表对象"}
        type="button"
      >
        {annotationsVisible
          ? <Eye aria-hidden="true" size={19} strokeWidth={1.7} />
          : <EyeOff aria-hidden="true" size={19} strokeWidth={1.7} />}
      </button>
      <button
        {...tooltipProps(
          annotationsLocked ? "解锁图表对象" : "锁定图表对象",
          annotationsLocked ? "允许拖动用户对象控制点" : "禁止误拖动用户对象",
        )}
        aria-label={annotationsLocked ? "解锁用户图表对象" : "锁定用户图表对象"}
        aria-pressed={annotationsLocked}
        className={annotationsLocked ? "utility-tool is-active" : "utility-tool"}
        disabled={disabled}
        onClick={onToggleLock}
        title={annotationsLocked ? "解锁图表对象" : "锁定图表对象"}
        type="button"
      >
        {annotationsLocked
          ? <Lock aria-hidden="true" size={19} strokeWidth={1.7} />
          : <Unlock aria-hidden="true" size={19} strokeWidth={1.7} />}
      </button>
      <button
        {...tooltipProps("删除选中对象", "删除后可以使用撤销恢复")}
        aria-label="删除选中的图表对象"
        className="utility-tool danger-tool"
        disabled={!canDelete || historyPending || disabled}
        onClick={onDelete}
        title="删除选中对象"
        type="button"
      >
        <Trash2 aria-hidden="true" size={18} strokeWidth={1.7} />
      </button>
      </aside>
      {lineMenuOpen && (
        <div
          aria-label="线类工具"
          className="drawing-tool-panel"
          id="line-tool-panel"
          ref={linePanelRef}
          role="menu"
          style={{ left: lineMenuPosition.left, top: lineMenuPosition.top }}
        >
          <header>
            <strong>线类工具</strong>
            <span>点击第一点后即可实时预览</span>
          </header>
          {LINE_TOOL_SECTIONS.map((section) => (
            <section key={section.label}>
              <h3>{section.label}</h3>
              <div>
                {section.tools.map((tool) => {
                  const definition = drawingDefinition(tool);
                  const Icon = TOOL_ICONS[tool];
                  return (
                    <button
                      aria-checked={activeTool === tool}
                      className={activeTool === tool ? "is-active" : ""}
                      key={tool}
                      onClick={() => selectLineTool(tool)}
                      role="menuitemradio"
                      title={definition.label}
                      type="button"
                    >
                      <Icon aria-hidden="true" size={18} strokeWidth={1.7} />
                      <span>
                        <strong>{definition.label}</strong>
                        <small>{definition.instruction}</small>
                      </span>
                      {DRAWING_SHORTCUT_LABELS[tool] && <kbd>{DRAWING_SHORTCUT_LABELS[tool]}</kbd>}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
      {advancedMenuOpen && (
        <div
          aria-label="分析工具"
          className="drawing-tool-panel"
          id="advanced-tool-panel"
          ref={advancedPanelRef}
          role="menu"
          style={{ left: lineMenuPosition.left, top: lineMenuPosition.top }}
        >
          <header><strong>专业分析工具</strong><span>所有工具均保存为可编辑图表对象</span></header>
          {ADVANCED_TOOL_SECTIONS.map((section) => (
            <section key={section.label}>
              <h3>{section.label}</h3>
              <div>{section.tools.map((tool) => {
                const definition = drawingDefinition(tool);
                const Icon = TOOL_ICONS[tool];
                return (
                  <button
                    aria-checked={activeTool === tool}
                    className={activeTool === tool ? "is-active" : ""}
                    key={tool}
                    onClick={() => {
                      setLastAdvancedTool(tool);
                      setAdvancedMenuOpen(false);
                      onSelect(tool);
                    }}
                    role="menuitemradio"
                    title={definition.label}
                    type="button"
                  >
                    <Icon aria-hidden="true" size={18} strokeWidth={1.7} />
                    <span><strong>{definition.label}</strong><small>{definition.instruction}</small></span>
                    {DRAWING_SHORTCUT_LABELS[tool] && <kbd>{DRAWING_SHORTCUT_LABELS[tool]}</kbd>}
                  </button>
                );
              })}</div>
            </section>
          ))}
        </div>
      )}
      {tooltip && (
        <div
          className="drawing-tool-tooltip"
          id="drawing-tool-tooltip"
          role="tooltip"
          style={{ left: tooltip.left, top: tooltip.top }}
        >
          <strong>{tooltip.label}</strong>
          {tooltip.detail && <span>{tooltip.detail}</span>}
        </div>
      )}
    </>
  );
}
