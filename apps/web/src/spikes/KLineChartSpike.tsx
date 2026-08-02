import { useEffect, useRef, useState } from "react";
import { init } from "klinecharts";
import { KLineChartAdapter } from "../chart/KLineChartAdapter";
import { FIXED_BTCUSDT_BARS } from "./fixedBtcData";

export function KLineChartSpike() {
  const hostRef = useRef<HTMLDivElement>(null);
  const adapterRef = useRef<KLineChartAdapter | undefined>(undefined);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [price, setPrice] = useState(67_420);
  const [event, setEvent] = useState("尚未创建订单线");

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const chart = init(host, {
      timezone: "Etc/UTC",
      styles: {
        grid: {
          horizontal: { color: "#20242d" },
          vertical: { color: "#20242d" },
        },
        candle: {
          bar: { upColor: "#22ab94", downColor: "#f23645", noChangeColor: "#888" },
        },
      },
    });
    if (!chart) throw new Error("Unable to initialize KLineChart");
    chart.setDataLoader({
      getBars: ({ callback }) => callback([...FIXED_BTCUSDT_BARS], false),
    });
    chart.setSymbol({ ticker: "BTCUSDT", pricePrecision: 2, volumePrecision: 2 });
    chart.setPeriod({ type: "minute", span: 15 });
    adapterRef.current = new KLineChartAdapter(chart, host);
    return () => adapterRef.current?.destroy();
  }, []);

  const create = () => {
    if (orderId) return;
    const id = adapterRef.current?.createOrderLine(price, {
      onSelect: () => setEvent("订单线已选中"),
      onMove: (_id, nextPrice) => {
        setPrice(nextPrice);
        setEvent(`订单线拖动至 ${nextPrice.toFixed(2)}`);
      },
      onDelete: () => {
        setOrderId(null);
        setEvent("订单线已由图表删除");
      },
    });
    if (id) {
      setOrderId(id);
      setEvent("订单线已创建；点击选中，按住拖动");
    }
  };

  const move = () => {
    if (!orderId) return;
    const nextPrice = price + 100;
    adapterRef.current?.moveOrderLine(orderId, nextPrice);
    setPrice(nextPrice);
    setEvent(`程序化移动至 ${nextPrice.toFixed(2)}`);
  };

  const remove = () => {
    if (!orderId) return;
    adapterRef.current?.deleteOrderLine(orderId);
    setOrderId(null);
    setEvent("订单线已删除");
  };

  return (
    <main className="spike-page">
      <header className="spike-header">
        <div><small>M0 可复现验证</small><h1>KLineChart Order Line Spike</h1></div>
        <div className="spike-actions">
          <button onClick={create} disabled={orderId !== null} type="button">创建</button>
          <button onClick={move} disabled={orderId === null} type="button">移动 +100</button>
          <button onClick={remove} disabled={orderId === null} type="button">删除</button>
        </div>
      </header>
      <section className="spike-status"><span>BTCUSDT · 15m · 固定 96 根 K 线</span><strong>{event}</strong></section>
      <div className="spike-chart" ref={hostRef} />
    </main>
  );
}
