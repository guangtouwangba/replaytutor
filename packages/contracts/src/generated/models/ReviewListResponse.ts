// Generated from Pydantic. Do not edit.

export type CreatedAt = string;
export type EpisodeCount = number;
export type RecurringPatterns = string[];
export type ReportUrl = string;
export type ReviewId = string;
export type AnnotationId = string;
export type Confidence = number;
export type Evidence = string;
export type Label = string;
export type Layer = "background" | "location" | "setup" | "trigger" | "execution" | "management";
export type Perspective = "decision_time" | "after_action";
export type Price = string;
export type Time = string;
export type Points = AnnotationPoint[];
export type RuleId = string;
export type SchemaVersion = "1.0";
export type Shape = "line" | "zone" | "marker" | "label" | "path";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type Verdict = "correct" | "improve" | "neutral" | "unknown";
export type Annotations = PriceActionAnnotation[];
export type Dimension = "background" | "location" | "setup" | "trigger" | "execution" | "management" | "outcome";
export type Evidence1 = string[];
export type Title = string;
export type Verdict1 = "correct" | "improve" | "unknown";
export type Dimensions = ReviewDimension[];
export type ClosedAt = string | null;
export type Commission = string;
export type Direction = "long" | "short";
export type EntryPrice = string;
export type EpisodeId = string;
export type ExitPrice = string | null;
export type FillCount = number;
export type OpenedAt = string;
export type PeakQty = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type RealizedPnl = string;
export type SchemaVersion1 = "1.0";
export type Status = "open" | "closed";
export type Symbol = string;
export type Improvements = string[];
export type MissingContext = string[];
export type Positives = string[];
export type ProcessOutcome =
  | "good_trade_profit"
  | "good_trade_loss"
  | "bad_trade_profit"
  | "bad_trade_loss"
  | "insufficient_evidence"
  | "open_trade";
export type Reviews1 = EpisodeReview[];
export type SchemaVersion2 = "1.0";
export type ScopeKind = "today" | "recent" | "trade";
export type ScopeValue = string;
export type TopImprovements = string[];
export type TopPositives = string[];
export type TotalCommission = string;
export type TotalRealizedPnl = string;
export type Reviews = ReviewArtifact[];
export type SchemaVersion3 = "1.0";

export interface ReviewListResponse {
  reviews: Reviews;
  schema_version?: SchemaVersion3;
}
export interface ReviewArtifact {
  created_at: CreatedAt;
  episode_count: EpisodeCount;
  recurring_patterns: RecurringPatterns;
  report_url: ReportUrl;
  review_id: ReviewId;
  reviews: Reviews1;
  schema_version?: SchemaVersion2;
  scope_kind: ScopeKind;
  scope_value: ScopeValue;
  top_improvements: TopImprovements;
  top_positives: TopPositives;
  total_commission: TotalCommission;
  total_realized_pnl: TotalRealizedPnl;
}
export interface EpisodeReview {
  annotations: Annotations;
  dimensions: Dimensions;
  episode: TradeEpisode;
  improvements: Improvements;
  missing_context: MissingContext;
  positives: Positives;
  process_outcome: ProcessOutcome;
}
export interface PriceActionAnnotation {
  annotation_id: AnnotationId;
  confidence: Confidence;
  evidence: Evidence;
  label: Label;
  layer: Layer;
  perspective: Perspective;
  points: Points;
  rule_id: RuleId;
  schema_version?: SchemaVersion;
  shape: Shape;
  timeframe: Timeframe;
  verdict: Verdict;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
export interface ReviewDimension {
  dimension: Dimension;
  evidence: Evidence1;
  title: Title;
  verdict: Verdict1;
}
export interface TradeEpisode {
  closed_at: ClosedAt;
  commission: Commission;
  direction: Direction;
  entry_price: EntryPrice;
  episode_id: EpisodeId;
  exit_price: ExitPrice;
  fill_count: FillCount;
  opened_at: OpenedAt;
  peak_qty: PeakQty;
  position_side: PositionSide;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion1;
  status: Status;
  symbol: Symbol;
}
