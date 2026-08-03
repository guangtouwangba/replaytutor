// Generated from Pydantic. Do not edit.

export type CumulativeNotional = string;
export type CumulativeQuantity = string;
export type Notional = string;
export type Price = string;
export type Quantity = string;

export interface MarketDepthLevel {
  cumulative_notional: CumulativeNotional;
  cumulative_quantity: CumulativeQuantity;
  notional: Notional;
  price: Price;
  quantity: Quantity;
}
