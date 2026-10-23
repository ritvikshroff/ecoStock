"use client";
import { EmptyState } from "./ui";

/** columns: [{ key, header, render?(row), className? }] */
export default function DataTable({ columns, rows, rowKey = "id", testid = "table", empty = "Nothing to show." }) {
  if (!rows.length) return <EmptyState text={empty} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" data-testid={testid}>
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            {columns.map((c) => <th key={c.key} className="whitespace-nowrap px-3 py-2 font-semibold">{c.header}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r[rowKey]} className="hover:bg-slate-50" data-testid={`${testid}-row`} data-id={r[rowKey]}>
              {columns.map((c) => (
                <td key={c.key} className={`whitespace-nowrap px-3 py-2.5 ${c.className || ""}`} data-col={c.key}>
                  {c.render ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
