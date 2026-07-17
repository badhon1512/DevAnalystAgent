"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";
import DataTable from "../../components/DataTable";
import { api } from "../../lib/api";
import type { ListResponse, Product } from "../../lib/types";

export default function Page() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [brand, setBrand] = useState("");

  const [data, setData] = useState<ListResponse<Product> | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const res = await api.products({ search, category, brand, limit: 50, offset: 0 });
      setData(res);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load products");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns = useMemo(
    () => [
      { key: "sku", label: "SKU" },
      { key: "name", label: "Name" },
      { key: "category", label: "Category" },
      { key: "brand", label: "Brand" },
      { key: "price", label: "Price" },
      { key: "currency", label: "Cur" },
      { key: "is_active", label: "Active" },
    ] as const,
    []
  );

  const labelStyle = { fontSize: 12, color: "#475569", marginBottom: 6, fontWeight: 800 };
  const inputStyle = {
    width: "100%",
    padding: 10,
    borderRadius: 10,
    border: "1px solid rgba(15,23,42,0.12)",
    background: "#ffffff",
    color: "#0f172a",
  };

  return (
    <AppShell title="Products">
      <div style={{ padding: 16, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "end" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={labelStyle}>Search</div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="SKU or name..."
            style={inputStyle}
          />
        </div>

        <div style={{ minWidth: 180 }}>
          <div style={labelStyle}>Category</div>
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g., Electronics"
            style={inputStyle}
          />
        </div>

        <div style={{ minWidth: 180 }}>
          <div style={labelStyle}>Brand</div>
          <input
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            placeholder="e.g., NovaWorks"
            style={inputStyle}
          />
        </div>

        <button
          onClick={load}
          style={{ height: 42, padding: "0 14px", borderRadius: 10, border: "1px solid rgba(37,99,235,0.35)", background: "#2563eb", color: "#ffffff", fontWeight: 800 }}
        >
          Apply
        </button>
      </div>

      <div style={{ padding: 16, paddingTop: 0, color: "#64748b", fontSize: 12 }}>
        {loading ? "Loading..." : err ? `Error: ${err}` : data ? `Showing ${data.items.length} of ${data.total}` : ""}
      </div>

      <DataTable columns={columns} rows={data?.items || []} />
    </AppShell>
  );
}
