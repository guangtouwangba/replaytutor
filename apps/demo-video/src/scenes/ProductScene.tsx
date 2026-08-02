import { AbsoluteFill, Img, Easing, interpolate, staticFile, useCurrentFrame } from "remotion";

export function ProductScene({ image, eyebrow, caption, focus }: { image: string; eyebrow: string; caption: string; focus: "left" | "center" | "right" }) {
  const frame = useCurrentFrame();
  const x = focus === "left" ? 1 : focus === "right" ? -1 : 0;
  return <AbsoluteFill style={{ backgroundColor: "#080b10", overflow: "hidden" }}>
    <Img src={staticFile(image)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.76, scale: interpolate(frame, [0, 180], [1.02, 1.09], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }), translate: `${x * interpolate(frame, [0, 180], [0, 34], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px 0` }} />
    <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(8,11,16,.06), rgba(8,11,16,.9))" }} />
    <div style={{ position: "absolute", left: 120, right: 120, bottom: 105 }}>
      <div style={{ color: "#72adff", fontFamily: "ui-monospace, monospace", fontSize: 25, letterSpacing: 4 }}>{eyebrow}</div>
      <div style={{ color: "white", fontFamily: "Inter, system-ui, sans-serif", fontSize: 48, lineHeight: 1.16, fontWeight: 650, maxWidth: 1440, marginTop: 18, opacity: interpolate(frame, [8, 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{caption}</div>
    </div>
  </AbsoluteFill>;
}
