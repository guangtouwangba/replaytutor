// Generated from Pydantic. Do not edit.

/**
 * @maxItems 32
 */
export type ContextAnnotationIds = string[];
export type Locale = "en-US" | "zh-CN";
export type Question = string;
export type Stage = "environment" | "plan" | "position" | "exit" | "after_action";

export interface TutorRequest {
  context_annotation_ids?: ContextAnnotationIds;
  locale?: Locale;
  question: Question;
  stage?: Stage;
}
