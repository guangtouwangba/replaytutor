import type { AnnotationDisposition } from "@replaytutor/contracts";

export interface ChartTradePlanContext {
  readonly annotationId: string;
  readonly label: string;
  readonly side: "BUY" | "SELL";
  readonly entryPrice: string;
  readonly stopPrice: string;
  readonly targetPrice: string;
  readonly riskRewardRatio: string;
}

const POSITION_TOOLS = new Set(["long_position", "short_position", "risk_reward"]);

function decimalMetadata(
  metadata: Readonly<Record<string, string>>,
  key: string,
): string | null {
  const value = metadata[key];
  if (!value || !Number.isFinite(Number(value))) return null;
  return value;
}

export function chartTradePlanContext(
  disposition: AnnotationDisposition | null | undefined,
): ChartTradePlanContext | null {
  if (!disposition || ["rejected", "deleted"].includes(disposition.state)) return null;
  const metadata = disposition.effective_metadata ?? {};
  const tool = disposition.original_annotation.tool ?? metadata.drawing_kind;
  if (!POSITION_TOOLS.has(tool)) return null;

  const entryPrice = decimalMetadata(metadata, "entry_price");
  const stopPrice = decimalMetadata(metadata, "stop_price");
  const targetPrice = decimalMetadata(metadata, "target_price");
  const riskRewardRatio = decimalMetadata(metadata, "risk_reward_ratio");
  if (!entryPrice || !stopPrice || !targetPrice || !riskRewardRatio) return null;

  const fallbackSide = tool === "short_position" ? "short" : "long";
  return {
    annotationId: disposition.annotation_id,
    label: disposition.effective_label,
    side: (metadata.side ?? fallbackSide) === "short" ? "SELL" : "BUY",
    entryPrice,
    stopPrice,
    targetPrice,
    riskRewardRatio,
  };
}
