import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

export function TitleScene({ title, detail }: { title: string; detail: string }) {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{ background: "radial-gradient(circle at 70% 20%, #17315a 0, #0c111b 48%, #080b10 100%)", color: "#f5f7fb", justifyContent: "center", padding: "100px 150px" }}>
    <div style={{ color: "#68a7ff", fontFamily: "ui-monospace, monospace", fontSize: 28, letterSpacing: 5 }}>REPLAYTUTOR · LOCAL ALPHA</div>
    <h1 style={{ fontFamily: "Inter, system-ui, sans-serif", fontSize: 92, lineHeight: 1.02, maxWidth: 1400, margin: "30px 0", opacity: interpolate(frame, [0, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }), translate: `0 ${interpolate(frame, [0, 24], [30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) })}px` }}>{title}</h1>
    <p style={{ color: "#aab5c6", fontFamily: "Inter, system-ui, sans-serif", fontSize: 42, margin: 0 }}>{detail}</p>
  </AbsoluteFill>;
}
