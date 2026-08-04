import { useCallback, useEffect, useState, type RefObject } from "react";

export interface ElementFullscreenControl {
  readonly active: boolean;
  readonly fallback: boolean;
  readonly toggle: () => Promise<void>;
}

export function useElementFullscreen<T extends HTMLElement>(
  targetRef: RefObject<T | null>,
): ElementFullscreenControl {
  const [nativeActive, setNativeActive] = useState(false);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const syncNativeState = () => setNativeActive(document.fullscreenElement === targetRef.current);
    document.addEventListener("fullscreenchange", syncNativeState);
    syncNativeState();
    return () => document.removeEventListener("fullscreenchange", syncNativeState);
  }, [targetRef]);

  useEffect(() => {
    const syncEscapeExit = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setNativeActive(false);
      setFallback(false);
    };
    window.addEventListener("keydown", syncEscapeExit, true);
    return () => window.removeEventListener("keydown", syncEscapeExit, true);
  }, []);

  const toggle = useCallback(async () => {
    const target = targetRef.current;
    if (!target) return;
    if (document.fullscreenElement === target) {
      await document.exitFullscreen();
      return;
    }
    if (fallback) {
      setFallback(false);
      return;
    }
    if (typeof target.requestFullscreen !== "function") {
      setFallback(true);
      return;
    }
    try {
      await target.requestFullscreen();
    } catch {
      setFallback(true);
    }
  }, [fallback, targetRef]);

  return { active: nativeActive || fallback, fallback, toggle };
}
