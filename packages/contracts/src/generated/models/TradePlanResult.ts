// Generated from Pydantic. Do not edit.

export type ExecutedAt = string;
export type Fee = string;
export type FillId = string;
export type FrameId = string;
export type OrderId = string;
export type Price = string;
export type Quantity = string;
export type QuoteAmount = string;
export type SchemaVersion = "1.0";
export type SessionId = string;
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
export type SchemaVersion1 = "1.0";
export type SessionId1 = string;
export type Side1 = "BUY" | "SELL";
export type Status = "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;
export type Orders = PaperOrder[];
export type CreatedAt = string;
export type EntryPrice = string | null;
export type FrameId1 = string;
export type Invalidation = string;
export type PlanId1 = string;
export type RiskAmount = string;
export type SchemaVersion2 = "1.0";
export type SessionId2 = string;
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
export type SchemaVersion3 = "1.0";
export type SchemaVersion4 = "1.0";
export type IdempotentReplay = boolean;
export type SchemaVersion5 = "1.0";
export type CreatedAt1 = string;
export type DeletedAt = string | null;
export type Fingerprint = string;
export type CurrentIndex = number;
export type FrameId2 = string;
export type Progress = number;
export type Revision = number;
export type SchemaVersion6 = "1.0";
export type SessionId3 = string;
export type TotalBars = number;
export type VisibleAt = string;
export type HiddenRealDate = boolean;
export type InitialCash = string;
export type AssetClass = "crypto_spot" | "crypto_perpetual" | "equity";
export type BaseCurrency = string;
export type CanonicalSymbol = string;
export type DisplayName = string;
export type InstrumentId = string;
export type LotSize = string;
export type Market = "CRYPTO" | "CN";
export type MarketRuleSetId = string;
export type PriceScale = number;
export type QuoteCurrency = string;
export type SchemaVersion7 = "1.0";
export type TickSize = string;
export type Timezone = string;
export type Venue = string;
export type PlaybookId = string | null;
export type Revision1 = number;
export type SchemaVersion8 = "1.0";
export type Seed = number;
export type SessionId4 = string;
export type SnapshotId = string;
export type StartIndex = number;
export type Status2 = "ready" | "paused" | "completed" | "stopped";
export type Timeframe = "1m";
export type UpdatedAt = string;
export type WarmupBars = number;

export interface TradePlanResult {
  execution: ExecutionSnapshot;
  idempotent_replay?: IdempotentReplay;
  schema_version?: SchemaVersion5;
  session: ReplaySession;
}
export interface ExecutionSnapshot {
  fills?: Fills;
  orders?: Orders;
  plan?: TradePlan | null;
  portfolio: PortfolioState;
  schema_version?: SchemaVersion4;
}
export interface PaperFill {
  executed_at: ExecutedAt;
  fee: Fee;
  fill_id: FillId;
  frame_id: FrameId;
  order_id: OrderId;
  price: Price;
  quantity: Quantity;
  quote_amount: QuoteAmount;
  schema_version?: SchemaVersion;
  session_id: SessionId;
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
  schema_version?: SchemaVersion1;
  session_id: SessionId1;
  side: Side1;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
}
export interface TradePlan {
  created_at: CreatedAt;
  entry_price?: EntryPrice;
  frame_id: FrameId1;
  invalidation: Invalidation;
  plan_id: PlanId1;
  risk_amount: RiskAmount;
  schema_version?: SchemaVersion2;
  session_id: SessionId2;
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
  schema_version?: SchemaVersion3;
}
export interface ReplaySession {
  created_at: CreatedAt1;
  deleted_at?: DeletedAt;
  fingerprint: Fingerprint;
  frame: ReplayFrame;
  hidden_real_date: HiddenRealDate;
  initial_cash: InitialCash;
  instrument: Instrument;
  playbook_id?: PlaybookId;
  revision: Revision1;
  schema_version?: SchemaVersion8;
  seed: Seed;
  session_id: SessionId4;
  snapshot_id: SnapshotId;
  start_index: StartIndex;
  status: Status2;
  timeframe?: Timeframe;
  updated_at: UpdatedAt;
  warmup_bars: WarmupBars;
}
export interface ReplayFrame {
  current_index: CurrentIndex;
  frame_id: FrameId2;
  progress: Progress;
  revision: Revision;
  schema_version?: SchemaVersion6;
  session_id: SessionId3;
  total_bars: TotalBars;
  visible_at: VisibleAt;
}
export interface Instrument {
  asset_class: AssetClass;
  base_currency: BaseCurrency;
  canonical_symbol: CanonicalSymbol;
  display_name: DisplayName;
  instrument_id: InstrumentId;
  lot_size: LotSize;
  market: Market;
  market_rule_set_id: MarketRuleSetId;
  price_scale: PriceScale;
  quote_currency: QuoteCurrency;
  schema_version?: SchemaVersion7;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
