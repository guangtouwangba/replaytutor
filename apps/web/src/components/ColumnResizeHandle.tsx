import { useRef, type PointerEvent as ReactPointerEvent } from "react";

export function clampResizableValue(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function readStoredResizableValue(
  key: string,
  fallback: number,
  min: number,
  max: number,
) {
  if (typeof window === "undefined") return fallback;
  const stored = window.localStorage.getItem(key);
  if (stored === null || stored.trim() === "") return fallback;
  const parsed = Number(stored);
  return Number.isFinite(parsed) ? clampResizableValue(parsed, min, max) : fallback;
}

export function ColumnResizeHandle({
  className = "",
  direction = 1,
  label,
  max,
  min,
  multiplier = 1,
  onChange,
  onReset,
  value,
}: {
  readonly className?: string;
  readonly direction?: 1 | -1;
  readonly label: string;
  readonly max: number;
  readonly min: number;
  readonly multiplier?: number;
  readonly onChange: (value: number) => void;
  readonly onReset: () => void;
  readonly value: number;
}) {
  const drag = useRef<{ pointerId: number; startX: number; startValue: number } | null>(null);
  const updateFromPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    const delta = (event.clientX - drag.current.startX) * direction * multiplier;
    onChange(clampResizableValue(drag.current.startValue + delta, min, max));
  };
  const stopDragging = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    drag.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  return (
    <div
      aria-label={label}
      aria-orientation="vertical"
      aria-valuemax={max}
      aria-valuemin={min}
      aria-valuenow={Math.round(value)}
      className={`column-resize-handle ${className}`}
      onDoubleClick={onReset}
      onKeyDown={(event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const physicalDelta = event.key === "ArrowLeft" ? -16 : 16;
        onChange(clampResizableValue(value + physicalDelta * direction * multiplier, min, max));
      }}
      onPointerCancel={stopDragging}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        drag.current = { pointerId: event.pointerId, startX: event.clientX, startValue: value };
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={updateFromPointer}
      onPointerUp={stopDragging}
      role="separator"
      tabIndex={0}
      title={`${label} · 双击复位`}
    >
      <span aria-hidden="true" />
    </div>
  );
}
