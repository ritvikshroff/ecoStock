"use client";
import { useState } from "react";
import { Loader2, RefreshCw, Check } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { MARKDOWN_TIERS, daysToExpiry, fefoSort, isNearExpiry, money } from "@/lib/logic";
import { Badge, Button, Card, Modal, PageHeader } from "../ui";
import DataTable from "../DataTable";

export default function Pricing() {
  const { batches, applyMarkdown, sync } = useStore();
  const [selected, setSelected] = useState([]);
  const [pct, setPct] = useState(null);
  const [confirm, setConfirm] = useState(false);
  const rows = fefoSort(batches.filter((b) => isNearExpiry(b)));
  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  const allSelected = rows.length > 0 && rows.every((r) => selected.includes(r.id));

  const columns = [
    { key: "sel", header: <input type="checkbox" aria-label="Select all" data-testid="select-all" checked={allSelected} onChange={() => setSelected(allSelected ? [] : rows.map((r) => r.id))} />, render: (r) => <input type="checkbox" data-testid={`select-${r.batchNo}`} checked={selected.includes(r.id)} onChange={() => toggle(r.id)} /> },
    { key: "batchNo", header: "Batch", className: "font-mono" },
    { key: "product", header: "Product", className: "font-medium text-slate-900" },
    { key: "qty", header: "Qty" },
    { key: "days", header: "Days left", render: (r) => daysToExpiry(r.expiry) },
    { key: "price", header: "Price", render: (r) => (r.discountedPrice ? (<><s className="text-slate-400">{money(r.price)}</s> <b data-testid={`price-${r.batchNo}`}>{money(r.discountedPrice)}</b></>) : <span data-testid={`price-${r.batchNo}`}>{money(r.price)}</span>) },
    { key: "disc", header: "Markdown", render: (r) => (r.discountPct ? <Badge tone="bg-sky-100 text-sky-800">{r.discountPct}% off</Badge> : "—") },
    { key: "sync", header: "POS / ESL sync", render: (r) => <SyncCell state={sync[r.id]} batchNo={r.batchNo} /> },
  ];

  const run = () => {
    const res = applyMarkdown(selected, pct);
    if (res.ok) { setConfirm(false); setSelected([]); setPct(null); }
  };

  return (
    <>
      <PageHeader title="Dynamic Pricing" subtitle="Items expiring within 3 days. Apply a markdown and push it to POS & electronic shelf labels." />
      <Card
        title={`Near-expiry items (${rows.length})`}
        action={
          <div className="flex items-center gap-2">
            {MARKDOWN_TIERS.map((t) => (
              <button key={t} data-testid={`tier-${t}`} onClick={() => setPct(t)} className={`rounded-lg border px-3 py-1.5 text-sm font-semibold ${pct === t ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"}`}>{t}%</button>
            ))}
            <Button data-testid="apply-markdown" disabled={!selected.length || !pct} onClick={() => setConfirm(true)}>Apply markdown</Button>
          </div>
        }
      >
        <DataTable testid="pricing-table" columns={columns} rows={rows} empty="No items expiring in the next 3 days." />
      </Card>
      <Modal open={confirm} title="Confirm markdown" onClose={() => setConfirm(false)} testid="confirm-modal">
        <p className="text-sm text-slate-600">Apply <b>{pct}% off</b> to <b>{selected.length}</b> batch(es) and sync prices to the POS and shelf labels?</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setConfirm(false)} data-testid="confirm-cancel">Cancel</Button>
          <Button onClick={run} data-testid="confirm-apply">Confirm &amp; sync</Button>
        </div>
      </Modal>
    </>
  );
}

function SyncCell({ state, batchNo }) {
  if (state === "syncing") return <span className="inline-flex items-center gap-1 text-amber-700" data-testid={`sync-${batchNo}`} data-state="syncing"><Loader2 size={14} className="animate-spin" /> Syncing…</span>;
  if (state === "synced") return <span className="inline-flex items-center gap-1 text-emerald-700" data-testid={`sync-${batchNo}`} data-state="synced"><Check size={14} /> Synced</span>;
  return <span className="inline-flex items-center gap-1 text-slate-400" data-testid={`sync-${batchNo}`} data-state="idle"><RefreshCw size={14} /> Idle</span>;
}
