"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";
import DataTable from "../../components/DataTable";
import { api } from "../../lib/api";
import type { ListResponse, InventoryRow } from "../../lib/types";

const PAGE_SIZE = 20;

export default function Page() {
  // filters
  const [search, setSearch] = useState("");
  const [warehouseCode, setWarehouseCode] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);

  // pagination
  const [offset, setOffset] = useState(0);

  // data
  const [data, setData] = useState<ListResponse<InventoryRow> | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load(nextOffset = offset) {
    setLoading(true);
    setErr("");
    try {
      const res = await api.inventory({
        search,
        warehouse_code: warehouseCode || undefined,
        low_stock: lowStockOnly ? 1 : undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });

      setData(res);
      setOffset(nextOffset);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load inventory");
    } finally {
      setLoading(false);
    }
  }

  // initial load
  useEffect(() => {
    load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns = useMemo(
    () =>
      [
        { key: "sku", label: "SKU" },
        { key: "product_name", label: "Product" },
        { key: "warehouse_name", label: "Warehouse" },
        { key: "stock_on_hand", label: "Stock" },
        { key: "reorder_point", label: "Reorder Point" },
        { key: "updated_at", label: "Updated At" },
      ] as const,
    []
  );

  const total = data?.total ?? 0;
  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + (data?.items.length ?? 0), total);

  return (
    <AppShell title="Inventory">
      {/* Filters */}
      <div
        style={{
          padding: 16,
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          alignItems: "end",
        }}
      >
        {/* Search */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
            Search
          </div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="SKU or product name..."
            style={{
              width: "100%",
              padding: 10,
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(2,6,23,0.35)",
              color: "inherit",
            }}
          />
        </div>

        {/* Warehouse dropdown (static for now) */}
        <div style={{ minWidth: 180 }}>
          <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
            Warehouse
          </div>
          <select
            value={warehouseCode}
            onChange={(e) => setWarehouseCode(e.target.value)}
            style={{
              width: "100%",
              padding: 10,
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(2,6,23,0.35)",
              color: "inherit",
            }}
          >
            <option value="">All</option>
            <option value="WH-MUC">WH-MUC</option>
            <option value="WH-BER">WH-BER</option>
            <option value="WH-FRA">WH-FRA</option>
          </select>
        </div>

        {/* Low stock checkbox */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            paddingBottom: 6,
            color: "#cbd5e1",
          }}
        >
          <input
            type="checkbox"
            checked={lowStockOnly}
            onChange={(e) => setLowStockOnly(e.target.checked)}
          />
          Low stock only
        </label>

        {/* Apply */}
        <button
          onClick={() => load(0)}
          style={{
            height: 42,
            padding: "0 14px",
            borderRadius: 10,
            border: "1px solid rgba(37,99,235,0.35)",
            background: "rgba(37,99,235,0.25)",
            color: "inherit",
            fontWeight: 700,
          }}
        >
          Apply
        </button>
      </div>

      {/* Status */}
      <div
        style={{
          padding: "0 16px 12px",
          color: "#94a3b8",
          fontSize: 12,
        }}
      >
        {loading
          ? "Loading..."
          : err
          ? `Error: ${err}`
          : data
          ? `Showing ${showingFrom}-${showingTo} of ${total}`
          : ""}
      </div>

      {/* Table */}
      <DataTable columns={columns} rows={data?.items || []} />

      {/* Pagination */}
      <div
        style={{
          padding: 16,
          display: "flex",
          gap: 10,
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <button
          onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
          disabled={loading || offset === 0}
          style={{
            height: 38,
            padding: "0 12px",
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(2,6,23,0.35)",
            color: "inherit",
            opacity: offset === 0 ? 0.5 : 1,
          }}
        >
          Prev
        </button>

        <button
          onClick={() => load(offset + PAGE_SIZE)}
          disabled={loading || offset + PAGE_SIZE >= total}
          style={{
            height: 38,
            padding: "0 12px",
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(2,6,23,0.35)",
            color: "inherit",
            opacity: offset + PAGE_SIZE >= total ? 0.5 : 1,
          }}
        >
          Next
        </button>
      </div>
    </AppShell>
  );
}
