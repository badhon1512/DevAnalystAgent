"use client";

import { useMemo } from "react";

type Col<T> = { key: keyof T; label: string };

export default function DataTable<T extends object>({
  columns,
  rows,
}: {
  columns: readonly Col<T>[];
  rows: T[];
}) {
  const keys = useMemo(() => columns.map((c) => c.key), [columns]);

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={String(c.key)}
                style={{
                  textAlign: "left",
                  fontSize: 12,
                  color: "#475569",
                  padding: "12px 12px",
                  borderBottom: "1px solid rgba(15,23,42,0.08)",
                  background: "#f8fafc",
                  fontWeight: 800,
                }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx} style={{ borderBottom: "1px solid rgba(15,23,42,0.06)" }}>
              {keys.map((k) => (
                <td key={String(k)} style={{ padding: "12px 12px", color: "#0f172a", fontSize: 13 }}>
                  {String(r[k] ?? "")}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} style={{ padding: 16, color: "#64748b" }}>
                No results
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
