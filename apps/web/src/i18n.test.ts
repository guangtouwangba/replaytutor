import { beforeEach, describe, expect, it } from "vitest";
import i18n, { applyLocale, currentLocale, resolveLocale } from "./i18n";

describe("i18n", () => {
  beforeEach(() => window.localStorage.clear());

  it("falls back to English for unsupported system locales", () => {
    expect(resolveLocale("en-US")).toBe("en-US");
    expect(resolveLocale("zh-CN")).toBe("zh-CN");
  });

  it("updates document language and stable local preference", async () => {
    await applyLocale("zh-CN");
    expect(currentLocale()).toBe("zh-CN");
    expect(document.documentElement.lang).toBe("zh-CN");
    expect(i18n.t("home.hero")).toContain("当时可见");
    await applyLocale("en-US");
  });
});
