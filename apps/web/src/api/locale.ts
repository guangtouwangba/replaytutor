import { currentLocale } from "../i18n";

export function localeHeaders(headers: HeadersInit = {}): Headers {
  const merged = new Headers(headers);
  merged.set("Accept-Language", currentLocale());
  return merged;
}
