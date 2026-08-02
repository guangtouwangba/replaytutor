// Generated from Pydantic. Do not edit.

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
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type Quantity = string;
export type UnrealizedPnl = string;
export type Positions = PositionState[];
export type RealizedPnl = string;
export type SchemaVersion = "1.0";
export type UnrealizedPnl1 = string;
export type UsedInitialMargin = string;
export type WalletBalance = string;

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
  schema_version?: SchemaVersion;
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
  position_side: PositionSide;
  quantity: Quantity;
  unrealized_pnl: UnrealizedPnl;
}
