import { registerOverlay, type Coordinate, type OverlayFigure, type OverlayTemplate } from "klinecharts";

export const REPLAY_CUSTOM_OVERLAYS = [
  "replayRect",
  "replayRiskReward",
  "replayPolyline",
  "replayLevels",
  "replayHorizontalLine",
] as const;

type ReplayCustomOverlay = typeof REPLAY_CUSTOM_OVERLAYS[number];

let registered = false;

function rectangleCoordinates(first: Coordinate, second: Coordinate): Coordinate[] {
  return [
    { x: first.x, y: first.y },
    { x: second.x, y: first.y },
    { x: second.x, y: second.y },
    { x: first.x, y: second.y },
  ];
}

const replayRect: OverlayTemplate = {
  name: "replayRect",
  totalStep: 3,
  needDefaultPointFigure: true,
  createPointFigures: ({ coordinates }) => {
    if (coordinates.length < 2) return [];
    return [{
      key: "area",
      type: "polygon",
      attrs: { coordinates: rectangleCoordinates(coordinates[0], coordinates[1]) },
    }];
  },
};

const replayRiskReward: OverlayTemplate = {
  name: "replayRiskReward",
  totalStep: 4,
  needDefaultPointFigure: true,
  createPointFigures: ({ coordinates }) => {
    if (coordinates.length < 3) return [];
    const [entry, stop, target] = coordinates;
    return [
      {
        key: "risk",
        type: "polygon",
        attrs: { coordinates: rectangleCoordinates(entry, stop) },
        styles: { color: "#f2687d2e", borderColor: "#f2687d", borderSize: 1 },
      },
      {
        key: "reward",
        type: "polygon",
        attrs: { coordinates: rectangleCoordinates(entry, target) },
        styles: { color: "#25c7922e", borderColor: "#25c792", borderSize: 1 },
      },
    ];
  },
};

const replayPolyline: OverlayTemplate = {
  name: "replayPolyline",
  totalStep: 17,
  needDefaultPointFigure: true,
  createPointFigures: ({ coordinates }) => coordinates.length < 2 ? [] : [{
    key: "path",
    type: "line",
    attrs: { coordinates },
  }],
};

const LEVEL_RATIOS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.618];

const replayLevels: OverlayTemplate = {
  name: "replayLevels",
  totalStep: 3,
  needDefaultPointFigure: true,
  createPointFigures: ({ coordinates }) => {
    if (coordinates.length < 2) return [];
    const [start, end] = coordinates;
    return LEVEL_RATIOS.map((ratio): OverlayFigure => {
      const y = start.y + ((end.y - start.y) * ratio);
      return {
        key: `level-${ratio}`,
        type: "line",
        attrs: { coordinates: [{ x: start.x, y }, { x: end.x, y }] },
      };
    });
  },
};

const replayHorizontalLine: OverlayTemplate = {
  name: "replayHorizontalLine",
  totalStep: 2,
  needDefaultPointFigure: true,
  needDefaultYAxisFigure: false,
  createPointFigures: ({ coordinates, bounding }) => coordinates.length < 1 ? [] : [{
    key: "horizontal-line",
    type: "line",
    attrs: {
      coordinates: [
        { x: 0, y: coordinates[0].y },
        { x: bounding.width, y: coordinates[0].y },
      ],
    },
  }],
  createYAxisFigures: ({ chart, coordinates, bounding, overlay }) => {
    const value = overlay.points[0]?.value;
    if (coordinates.length < 1 || typeof value !== "number" || !Number.isFinite(value)) return [];
    const precision = chart.getSymbol()?.pricePrecision ?? 2;
    const color = overlay.styles?.line?.color ?? "#20b7f5";
    const text = value.toLocaleString("en-US", {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });
    return [
      {
        key: "price-label-background",
        type: "rect",
        attrs: { x: 0, y: coordinates[0].y - 13, width: bounding.width, height: 26 },
        styles: { style: "fill", color, borderColor: color, borderSize: 0, borderRadius: 3 },
        ignoreEvent: true,
      },
      {
        key: "price-label-text",
        type: "text",
        attrs: {
          x: bounding.width - 6,
          y: coordinates[0].y,
          text,
          align: "right",
          baseline: "middle",
        },
        styles: { color: "#ffffff", size: 11, weight: 600 },
        ignoreEvent: true,
      },
    ];
  },
};

export function registerReplayOverlays(): void {
  if (registered) return;
  [replayRect, replayRiskReward, replayPolyline, replayLevels, replayHorizontalLine].forEach(registerOverlay);
  registered = true;
}

export function isReplayCustomOverlay(value: string): value is ReplayCustomOverlay {
  return REPLAY_CUSTOM_OVERLAYS.some((name) => name === value);
}
