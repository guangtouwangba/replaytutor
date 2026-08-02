import { Video } from "@remotion/media";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame } from "remotion";
import type { DemoLocale } from "../copy";

export function BrowserFootageScene({ locale }: { locale: DemoLocale }) {
  const frame = useCurrentFrame();
  const language = locale === "zh-CN" ? "中文界面 · 中文录制" : "ENGLISH UI · ENGLISH CAPTURE";
  const source = locale === "zh-CN"
    ? "recordings/replaytutor-browser-zh.webm"
    : "recordings/replaytutor-browser-en.webm";
  const scale = interpolate(frame, [0, 765], [1, 1.035], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return <AbsoluteFill style={{ background: "#070b11", alignItems: "center", justifyContent: "center" }}>
    <div style={{
      width: 1728,
      height: 1080,
      overflow: "hidden",
      position: "relative",
      transform: `scale(${scale})`,
      boxShadow: "0 36px 110px rgba(0,0,0,.48)",
    }}>
      <Video
        muted
        objectFit="cover"
        playbackRate={0.65}
        src={staticFile(source)}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
    <div style={{
      position: "absolute",
      left: 58,
      top: 42,
      padding: "12px 18px",
      borderRadius: 999,
      background: "rgba(7,11,17,.82)",
      border: "1px solid rgba(130,232,184,.38)",
      color: "#82e8b8",
      fontFamily: "Inter, ui-sans-serif, system-ui",
      fontSize: 21,
      fontWeight: 750,
      letterSpacing: ".08em",
    }}>{language}</div>
  </AbsoluteFill>;
}
