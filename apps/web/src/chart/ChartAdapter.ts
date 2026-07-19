export interface OrderLineCallbacks {
  readonly onSelect: (id: string) => void;
  readonly onMove: (id: string, price: number) => void;
  readonly onDelete: (id: string) => void;
}

export interface ChartAdapter {
  createOrderLine(price: number, callbacks: OrderLineCallbacks): string;
  moveOrderLine(id: string, price: number): void;
  deleteOrderLine(id: string): void;
  destroy(): void;
}
