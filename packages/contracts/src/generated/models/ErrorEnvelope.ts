// Generated from Pydantic. Do not edit.

export type Code = string;
export type Message = string;
export type RequestId = string;
export type Retryable = boolean;

export interface ErrorEnvelope {
  error: ErrorDetail;
}
export interface ErrorDetail {
  code: Code;
  details?: Details;
  message: Message;
  request_id: RequestId;
  retryable?: Retryable;
}
export interface Details {
  [k: string]: unknown;
}
