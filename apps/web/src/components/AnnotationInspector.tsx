import type { AnnotationDisposition, AnnotationPoint } from "@replaytutor/contracts";
import { useEffect, useState } from "react";

export function AnnotationInspector({
  disposition,
  pending,
  readOnly = false,
  onAction,
}: {
  readonly disposition: AnnotationDisposition | null;
  readonly pending: boolean;
  readonly readOnly?: boolean;
  readonly onAction: (
    action: "accepted" | "rejected" | "revised" | "deleted",
    label?: string,
    points?: AnnotationPoint[],
  ) => void;
}) {
  const [label, setLabel] = useState("");
  const [points, setPoints] = useState<AnnotationPoint[]>([]);
  useEffect(() => {
    setLabel(disposition?.effective_label ?? "");
    setPoints(disposition?.effective_points ?? []);
  }, [disposition]);

  if (!disposition) {
    return <div className="dock-card annotation-inspector"><span className="page-kicker">ANNOTATION INSPECTOR</span><p>在图层列表中选择一条标注进行检查。</p></div>;
  }
  const annotation = disposition.original_annotation;
  const visible = !["rejected", "deleted"].includes(disposition.state);
  return (
    <div className="dock-card annotation-inspector">
      <span className="page-kicker">ANNOTATION INSPECTOR</span>
      <div className="annotation-inspector-head">
        <strong>{annotation.layer === "ai" ? "AI 建议" : "用户标注"}</strong>
        <span>{disposition.state}</span>
      </div>
      <label>标注文字<input disabled={readOnly} maxLength={200} onChange={(event) => setLabel(event.target.value)} value={label} /></label>
      {points.map((point, index) => (
        <div className="annotation-point-editor" key={`${point.time}-${index}`}>
          <label>UTC 时间<input disabled={readOnly} onChange={(event) => setPoints((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, time: `${event.target.value}:00.000Z` } : item))} type="datetime-local" value={point.time.slice(0, 16)} /></label>
          <label>价格<input disabled={readOnly} onChange={(event) => setPoints((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, price: event.target.value } : item))} step="any" type="number" value={point.price} /></label>
        </div>
      ))}
      <div className="annotation-actions">
        {!readOnly && annotation.layer === "ai" && disposition.state === "proposed" && (
          <>
            <button disabled={pending} onClick={() => onAction("accepted")} type="button">接受</button>
            <button disabled={pending} onClick={() => onAction("rejected")} type="button">拒绝</button>
          </>
        )}
        {!readOnly && visible && <button disabled={pending || !label.trim()} onClick={() => onAction("revised", label, points)} type="button">保存修改</button>}
        {!readOnly && visible && <button className="danger-action" disabled={pending} onClick={() => onAction("deleted")} type="button">删除</button>}
      </div>
      <details>
        <summary>原始对象与来源</summary>
        <code>{annotation.annotation_id}</code>
        <p>{annotation.label}</p>
        {annotation.provenance_run_id && <code>{annotation.provenance_run_id}</code>}
      </details>
    </div>
  );
}
