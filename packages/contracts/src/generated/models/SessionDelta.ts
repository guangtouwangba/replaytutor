// Generated from Pydantic. Do not edit.

export type AnnotationId = string;
export type CreatedAt = string;
export type FrameId = string;
export type Label = string;
export type Layer = "user" | "ai";
/**
 * @minItems 1
 * @maxItems 4
 */
export type Points =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint];
export type Price = string;
export type Time = string;
export type ProvenanceRunId = string | null;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Shape = "line" | "zone" | "marker" | "label";
export type Annotations = ChartAnnotation[];
export type Close = string;
export type High = string;
export type Low = string;
export type Open = string;
export type Volume = string;
export type BarId = string;
export type CloseTime = string;
export type InstrumentId = string;
export type OpenTime = string;
export type QualityFlags = string[];
export type SchemaVersion1 = "1.0";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type Bars = Bar[];
export type EventId = string;
export type EventType = "session_created" | "replay_advanced" | "session_completed";
export type OccurredAt = string;
export type Revision = number;
export type Sequence = number;
export type SessionId1 = string;
export type Events = SessionEvent[];
export type ExecutedAt = string;
export type Fee = string;
export type FillId = string;
export type FrameId1 = string;
export type OrderId = string;
export type Price1 = string;
export type Quantity = string;
export type QuoteAmount = string;
export type SchemaVersion2 = "1.0";
export type SessionId2 = string;
export type Side = "BUY" | "SELL";
export type Fills = PaperFill[];
export type ActivateIndex = number;
export type FilledAt = string | null;
export type LimitPrice = string | null;
export type OcoGroupId = string | null;
export type OrderId1 = string;
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET";
export type ParentOrderId = string | null;
export type PlanId = string;
export type Quantity1 = string;
export type SchemaVersion3 = "1.0";
export type SessionId3 = string;
export type Side1 = "BUY" | "SELL";
export type Status = "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;
export type Orders = PaperOrder[];
export type CreatedAt1 = string;
export type EntryPrice = string | null;
export type FrameId2 = string;
export type Invalidation = string;
export type PlanId1 = string;
export type RiskAmount = string;
export type SchemaVersion4 = "1.0";
export type SessionId4 = string;
export type Side2 = "BUY" | "SELL";
export type Status1 = "locked";
export type StopPrice1 = string | null;
export type TargetPrice = string | null;
export type Thesis = string;
export type AverageEntryPrice = string;
export type Cash = string;
export type FeesPaid = string;
export type PositionQuantity = string;
export type RealizedPnl = string;
export type SchemaVersion5 = "1.0";
export type SchemaVersion6 = "1.0";
export type IdempotentReplay = boolean;
export type SchemaVersion7 = "1.0";
export type CreatedAt2 = string;
export type DeletedAt = string | null;
export type Fingerprint = string;
export type CurrentIndex = number;
export type FrameId3 = string;
export type Progress = number;
export type Revision1 = number;
export type SchemaVersion8 = "1.0";
export type SessionId5 = string;
export type TotalBars = number;
export type VisibleAt = string;
export type HiddenRealDate = boolean;
export type InitialCash = string;
export type AssetClass = "crypto_spot" | "crypto_perpetual" | "equity";
export type BaseCurrency = string;
export type CanonicalSymbol = string;
export type DisplayName = string;
export type InstrumentId1 = string;
export type LotSize = string;
export type Market = "CRYPTO" | "CN";
export type MarketRuleSetId = string;
export type PriceScale = number;
export type QuoteCurrency = string;
export type SchemaVersion9 = "1.0";
export type TickSize = string;
export type Timezone = string;
export type Venue = string;
export type PlaybookId = string | null;
export type Revision2 = number;
export type SchemaVersion10 = "1.0";
export type Seed = number;
export type SessionId6 = string;
export type SnapshotId = string;
export type StartIndex = number;
export type Status2 = "ready" | "paused" | "completed" | "stopped";
export type Timeframe1 = "1m";
export type UpdatedAt = string;
export type WarmupBars = number;

export interface SessionDelta {
  annotations?: Annotations;
  bars: Bars;
  events: Events;
  execution?: ExecutionSnapshot | null;
  idempotent_replay?: IdempotentReplay;
  schema_version?: SchemaVersion7;
  session: ReplaySession;
}
export interface ChartAnnotation {
  annotation_id: AnnotationId;
  created_at: CreatedAt;
  frame_id: FrameId;
  label: Label;
  layer: Layer;
  points: Points;
  provenance_run_id?: ProvenanceRunId;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  shape: Shape;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
export interface Bar {
  adjusted?: PriceValues | null;
  bar_id: BarId;
  close_time: CloseTime;
  instrument_id: InstrumentId;
  open_time: OpenTime;
  quality_flags?: QualityFlags;
  raw: PriceValues;
  schema_version?: SchemaVersion1;
  timeframe: Timeframe;
}
export interface PriceValues {
  close: Close;
  high: High;
  low: Low;
  open: Open;
  volume: Volume;
}
export interface SessionEvent {
  event_id: EventId;
  event_type: EventType;
  occurred_at: OccurredAt;
  payload?: Payload;
  revision: Revision;
  sequence: Sequence;
  session_id: SessionId1;
}
export interface Payload {
  [k: string]: unknown;
}
export interface ExecutionSnapshot {
  fills?: Fills;
  orders?: Orders;
  plan?: TradePlan | null;
  portfolio: PortfolioState;
  schema_version?: SchemaVersion6;
}
export interface PaperFill {
  executed_at: ExecutedAt;
  fee: Fee;
  fill_id: FillId;
  frame_id: FrameId1;
  order_id: OrderId;
  price: Price1;
  quantity: Quantity;
  quote_amount: QuoteAmount;
  schema_version?: SchemaVersion2;
  session_id: SessionId2;
  side: Side;
}
export interface PaperOrder {
  activate_index: ActivateIndex;
  filled_at?: FilledAt;
  limit_price?: LimitPrice;
  oco_group_id?: OcoGroupId;
  order_id: OrderId1;
  order_type: OrderType;
  parent_order_id?: ParentOrderId;
  plan_id: PlanId;
  quantity: Quantity1;
  schema_version?: SchemaVersion3;
  session_id: SessionId3;
  side: Side1;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
}
export interface TradePlan {
  created_at: CreatedAt1;
  entry_price?: EntryPrice;
  frame_id: FrameId2;
  invalidation: Invalidation;
  plan_id: PlanId1;
  risk_amount: RiskAmount;
  schema_version?: SchemaVersion4;
  session_id: SessionId4;
  side: Side2;
  status: Status1;
  stop_price?: StopPrice1;
  target_price?: TargetPrice;
  thesis: Thesis;
}
export interface PortfolioState {
  average_entry_price: AverageEntryPrice;
  cash: Cash;
  fees_paid: FeesPaid;
  position_quantity: PositionQuantity;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion5;
}
export interface ReplaySession {
  created_at: CreatedAt2;
  deleted_at?: DeletedAt;
  fingerprint: Fingerprint;
  frame: ReplayFrame;
  hidden_real_date: HiddenRealDate;
  initial_cash: InitialCash;
  instrument: Instrument;
  playbook_id?: PlaybookId;
  revision: Revision2;
  schema_version?: SchemaVersion10;
  seed: Seed;
  session_id: SessionId6;
  snapshot_id: SnapshotId;
  start_index: StartIndex;
  status: Status2;
  timeframe?: Timeframe1;
  updated_at: UpdatedAt;
  warmup_bars: WarmupBars;
}
export interface ReplayFrame {
  current_index: CurrentIndex;
  frame_id: FrameId3;
  progress: Progress;
  revision: Revision1;
  schema_version?: SchemaVersion8;
  session_id: SessionId5;
  total_bars: TotalBars;
  visible_at: VisibleAt;
}
export interface Instrument {
  asset_class: AssetClass;
  base_currency: BaseCurrency;
  canonical_symbol: CanonicalSymbol;
  display_name: DisplayName;
  instrument_id: InstrumentId1;
  lot_size: LotSize;
  market: Market;
  market_rule_set_id: MarketRuleSetId;
  price_scale: PriceScale;
  quote_currency: QuoteCurrency;
  schema_version?: SchemaVersion9;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
