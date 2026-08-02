// Generated from Pydantic. Do not edit.

export type CommandId = string;
export type ExpectedRevision = number;
export type OrderId = string;

export interface CancelOrderRequest {
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  order_id: OrderId;
}
