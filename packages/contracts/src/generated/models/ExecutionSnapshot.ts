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
export type ActivationPrice = string | null;
export type AverageFillPrice = string;
export type CallbackRate = string | null;
export type ClosePosition = boolean;
export type FilledAt = string | null;
export type FilledQuantity = string;
export type GoodTillIndex = number | null;
export type LimitPrice = string | null;
export type OcoGroupId = string | null;
export type OrderId1 = string;
export type OrderType =
  | "MARKET"
  | "LIMIT"
  | "STOP_MARKET"
  | "STOP_LIMIT"
  | "TAKE_PROFIT_MARKET"
  | "TAKE_PROFIT_LIMIT"
  | "TRAILING_STOP_MARKET";
export type ParentOrderId = string | null;
export type PlanId = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type PostOnly = boolean;
export type Quantity1 = string;
export type ReduceOnly = boolean;
export type SchemaVersion1 = "1.0";
export type SessionId1 = string;
export type Side1 = "BUY" | "SELL";
export type Status = "PENDING" | "TRIGGERED" | "PARTIALLY_FILLED" | "FILLED" | "CANCELLED" | "EXPIRED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;
export type TimeInForce = "GTC" | "IOC" | "FOK" | "GTD";
export type TrailAnchorPrice = string | null;
export type TriggeredAtIndex = number | null;
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
export type AccountType = "SPOT" | "USDT_PERPETUAL";
export type AvailableBalance = string;
export type AverageEntryPrice = string;
export type Cash = string;
export type FeesPaid = string;
export type FundingPaid = string;
export type Liquidated = boolean;
export type MaintenanceMargin = string;
export type MarginBalance = string;
export type PositionQuantity = string;
export type AverageEntryPrice1 = string;
export type InitialMargin = string;
export type Leverage = number;
export type LiquidationPrice = string | null;
export type MaintenanceMargin1 = string;
export type MarkPrice = string;
export type Notional = string;
export type PositionSide1 = "BOTH" | "LONG" | "SHORT";
export type Quantity2 = string;
export type UnrealizedPnl = string;
export type Positions = PositionState[];
export type RealizedPnl = string;
export type SchemaVersion3 = "1.0";
export type UnrealizedPnl1 = string;
export type UsedInitialMargin = string;
export type WalletBalance = string;
export type SchemaVersion4 = "1.0";

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
  activation_price?: ActivationPrice;
  average_fill_price?: AverageFillPrice;
  callback_rate?: CallbackRate;
  close_position?: ClosePosition;
  filled_at?: FilledAt;
  filled_quantity?: FilledQuantity;
  good_till_index?: GoodTillIndex;
  limit_price?: LimitPrice;
  oco_group_id?: OcoGroupId;
  order_id: OrderId1;
  order_type: OrderType;
  parent_order_id?: ParentOrderId;
  plan_id: PlanId;
  position_side?: PositionSide;
  post_only?: PostOnly;
  quantity: Quantity1;
  reduce_only?: ReduceOnly;
  schema_version?: SchemaVersion1;
  session_id: SessionId1;
  side: Side1;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
  time_in_force?: TimeInForce;
  trail_anchor_price?: TrailAnchorPrice;
  triggered_at_index?: TriggeredAtIndex;
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
  account_type?: AccountType;
  available_balance?: AvailableBalance;
  average_entry_price: AverageEntryPrice;
  cash: Cash;
  fees_paid: FeesPaid;
  funding_paid?: FundingPaid;
  liquidated?: Liquidated;
  maintenance_margin?: MaintenanceMargin;
  margin_balance?: MarginBalance;
  position_quantity: PositionQuantity;
  positions?: Positions;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion3;
  unrealized_pnl?: UnrealizedPnl1;
  used_initial_margin?: UsedInitialMargin;
  wallet_balance?: WalletBalance;
}
export interface PositionState {
  average_entry_price: AverageEntryPrice1;
  initial_margin: InitialMargin;
  leverage: Leverage;
  liquidation_price?: LiquidationPrice;
  maintenance_margin: MaintenanceMargin1;
  mark_price: MarkPrice;
  notional: Notional;
  position_side: PositionSide1;
  quantity: Quantity2;
  unrealized_pnl: UnrealizedPnl;
}
