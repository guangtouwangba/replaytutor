// Generated from Pydantic. Do not edit.

export type Question = string;
export type Stage = "environment" | "plan" | "position" | "exit" | "after_action";

export interface TutorRequest {
  question: Question;
  stage?: Stage;
}
