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
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from "lucide-react";
import { type FocusEvent, type MouseEvent, useEffect, useRef, useState } from "react";
import {
  DRAWING_DEFINITIONS,
  FIBONACCI_TOOL_IDS,
  FIBONACCI_TOOL_SECTIONS,
  LINE_TOOL_IDS,
  LINE_TOOL_SECTIONS,
  PATTERN_TOOL_IDS,
  PATTERN_TOOL_SECTIONS,
  PREDICTION_TOOL_IDS,
  PREDICTION_TOOL_SECTIONS,
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
  readonly onZoomIn: () => void;
  readonly onZoomOut: () => void;
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
  onZoomIn,
  onZoomOut,
}: DrawingToolbarProps) {
  const lineLauncherRef = useRef<HTMLButtonElement>(null);
  const linePanelRef = useRef<HTMLDivElement>(null);
  const groupLauncherRef = useRef<HTMLButtonElement>(null);
  const groupPanelRef = useRef<HTMLDivElement>(null);
  const [lineMenuOpen, setLineMenuOpen] = useState(false);
  const [openGroup, setOpenGroup] = useState<"fibonacci" | "prediction" | "pattern" | null>(null);
  const [lineMenuPosition, setLineMenuPosition] = useState({ left: 0, top: 0 });
  const [lastLineTool, setLastLineTool] = useState<Exclude<DrawingTool, "select">>("trend_line");
  const [lastFibonacciTool, setLastFibonacciTool] = useState<Exclude<DrawingTool, "select">>("fibonacci_retracement");
  const [lastPredictionTool, setLastPredictionTool] = useState<Exclude<DrawingTool, "select">>("measure");
  const [lastPatternTool, setLastPatternTool] = useState<Exclude<DrawingTool, "select">>("head_shoulders");
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
    if (FIBONACCI_TOOL_IDS.some((tool) => tool === activeTool)) setLastFibonacciTool(activeTool as Exclude<DrawingTool, "select">);
    if (PREDICTION_TOOL_IDS.some((tool) => tool === activeTool)) setLastPredictionTool(activeTool as Exclude<DrawingTool, "select">);
    if (PATTERN_TOOL_IDS.some((tool) => tool === activeTool)) setLastPatternTool(activeTool as Exclude<DrawingTool, "select">);
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
    if (!openGroup) return;
    const close = (event: PointerEvent) => {
      const target = event.target as Node;
      if (groupLauncherRef.current?.contains(target) || groupPanelRef.current?.contains(target)) return;
      setOpenGroup(null);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };
    window.addEventListener("pointerdown", close);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [openGroup]);
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
    setOpenGroup(null);
    setLineMenuOpen((value) => !value);
  };
  const selectLineTool = (tool: Exclude<DrawingTool, "select">) => {
    setLastLineTool(tool);
    setLineMenuOpen(false);
    onSelect(tool);
  };
  const activeLineTool = LINE_TOOL_IDS.some((tool) => tool === activeTool);
  const LineLauncherIcon = TOOL_ICONS[lastLineTool];
  const groupConfig = openGroup === "fibonacci"
    ? { label: "斐波那契工具", detail: "波段、扩展与时间分析", sections: FIBONACCI_TOOL_SECTIONS }
    : openGroup === "prediction"
      ? { label: "预测与测量", detail: "仓位预测、成交量与区间测量", sections: PREDICTION_TOOL_SECTIONS }
      : openGroup === "pattern"
        ? { label: "图形形态", detail: "标注当前可见行情中的结构", sections: PATTERN_TOOL_SECTIONS }
        : null;
  const openToolGroup = (group: "fibonacci" | "prediction" | "pattern", event: MouseEvent<HTMLButtonElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    setLineMenuPosition({ left: bounds.right + 8, top: Math.max(8, Math.min(bounds.top, window.innerHeight - 560)) });
    groupLauncherRef.current = event.currentTarget;
    setTooltip(null);
    setLineMenuOpen(false);
    setOpenGroup((value) => value === group ? null : group);
  };
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
        {...tooltipProps("斐波那契工具", drawingDefinition(lastFibonacciTool).label)}
        aria-controls="group-tool-panel"
        aria-expanded={openGroup === "fibonacci"}
        aria-haspopup="menu"
        aria-label="斐波那契工具"
        aria-pressed={FIBONACCI_TOOL_IDS.some((tool) => tool === activeTool)}
        className={`${FIBONACCI_TOOL_IDS.some((tool) => tool === activeTool) ? "is-active" : ""} grouped-tool`}
        disabled={disabled}
        onClick={(event) => openToolGroup("fibonacci", event)}
        title={drawingDefinition(lastFibonacciTool).label}
        type="button"
      >
        {(() => { const Icon = TOOL_ICONS[lastFibonacciTool]; return <Icon aria-hidden="true" size={19} strokeWidth={1.7} />; })()}
        <ChevronRight aria-hidden="true" className="grouped-tool-chevron" size={10} strokeWidth={1.8} />
      </button>
      <button
        {...tooltipProps("预测与测量", "多空仓位、盈亏比、成交量与范围测量")}
        aria-controls="group-tool-panel"
        aria-expanded={openGroup === "prediction"}
        aria-haspopup="menu"
        aria-label="预测与测量"
        aria-pressed={PREDICTION_TOOL_IDS.some((tool) => tool === activeTool)}
        className={`${PREDICTION_TOOL_IDS.some((tool) => tool === activeTool) ? "is-active" : ""} grouped-tool`}
        disabled={disabled}
        onClick={(event) => openToolGroup("prediction", event)}
        title={drawingDefinition(lastPredictionTool).label}
        type="button"
      >
        <Ruler aria-hidden="true" size={19} strokeWidth={1.7} />
        <ChevronRight aria-hidden="true" className="grouped-tool-chevron" size={10} strokeWidth={1.8} />
      </button>
      <button
        {...tooltipProps("图形形态", "头肩、三角、平顶平底与自由形状")}
        aria-controls="group-tool-panel"
        aria-expanded={openGroup === "pattern"}
        aria-haspopup="menu"
        aria-label="图形形态"
        aria-pressed={PATTERN_TOOL_IDS.some((tool) => tool === activeTool)}
        className={`${PATTERN_TOOL_IDS.some((tool) => tool === activeTool) ? "is-active" : ""} grouped-tool`}
        disabled={disabled}
        onClick={(event) => openToolGroup("pattern", event)}
        title={drawingDefinition(lastPatternTool).label}
        type="button"
      >
        <GitBranch aria-hidden="true" size={19} strokeWidth={1.7} />
        <ChevronRight aria-hidden="true" className="grouped-tool-chevron" size={10} strokeWidth={1.8} />
      </button>
      {DRAWING_DEFINITIONS.filter((definition) => (
        !LINE_TOOL_IDS.some((tool) => tool === definition.tool)
        && !FIBONACCI_TOOL_IDS.some((tool) => tool === definition.tool)
        && !PREDICTION_TOOL_IDS.some((tool) => tool === definition.tool)
        && !PATTERN_TOOL_IDS.some((tool) => tool === definition.tool)
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
      <button
        {...tooltipProps("放大", "放大当前活动图表")}
        aria-label="放大当前图表"
        className="utility-tool zoom-tool tool-group-start"
        onClick={onZoomIn}
        title="放大"
        type="button"
      ><ZoomIn aria-hidden="true" size={20} strokeWidth={1.7} /></button>
      <button
        {...tooltipProps("缩小", "缩小当前活动图表")}
        aria-label="缩小当前图表"
        className="utility-tool zoom-tool"
        onClick={onZoomOut}
        title="缩小"
        type="button"
      ><ZoomOut aria-hidden="true" size={20} strokeWidth={1.7} /></button>
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
      {groupConfig && (
        <div
          aria-label={groupConfig.label}
          className="drawing-tool-panel"
          id="group-tool-panel"
          ref={groupPanelRef}
          role="menu"
          style={{ left: lineMenuPosition.left, top: lineMenuPosition.top }}
        >
          <header><strong>{groupConfig.label}</strong><span>{groupConfig.detail}</span></header>
          {groupConfig.sections.map((section) => (
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
                      if (FIBONACCI_TOOL_IDS.some((item) => item === tool)) setLastFibonacciTool(tool);
                      if (PREDICTION_TOOL_IDS.some((item) => item === tool)) setLastPredictionTool(tool);
                      if (PATTERN_TOOL_IDS.some((item) => item === tool)) setLastPatternTool(tool);
                      setOpenGroup(null);
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
