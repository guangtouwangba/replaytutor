# ADR 0001：KLineChart 订单线 Spike

状态：Accepted  
日期：2026-07-19

## 问题

MVP 需要渲染确定性 K 线，并让订单线支持创建、选择、拖动和删除。需要在进入回放与下单功能前确认 KLineChart 可以被稳定封装，而不把图表库 API 泄漏到业务模块。

## 实现与复现

- `apps/web/src/spikes/fixedBtcData.ts` 生成固定的 96 根 BTCUSDT 15 分钟 K 线，不请求网络。
- `apps/web/src/spikes/KLineChartSpike.tsx` 提供浏览器内创建、选择、拖动、程序化移动与删除验证页。
- `apps/web/src/chart/ChartAdapter.ts` 固化业务侧最小接口。
- `apps/web/src/chart/KLineChartAdapter.test.ts` 在测试中验证创建参数、选择回调、拖动结束回调、移动覆盖和删除。

```bash
make dev
open 'http://127.0.0.1:5173/?spike=kline'
pnpm --filter @replaytutor/web test
```

## 结论

采用 KLineChart 10 作为图表内核，订单线使用其 `horizontalStraightLine` overlay。业务代码只依赖 `ChartAdapter`，后续若在大规模订单线、命中区域或跨 pane 场景遇到限制，可以在 Adapter 内切换为 SVG overlay，不影响订单与回放领域模型。

当前 Spike 不实现订单语义、撮合、回放时间约束或持久化。
