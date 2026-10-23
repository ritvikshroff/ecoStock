"use client";
import { useState } from "react";
import { Send } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { CHANNELS } from "@/lib/mockData";
import { fefoSort, daysToExpiry } from "@/lib/logic";
import { Button, Card, FormError, PageHeader, inputCls } from "../ui";
import DataTable from "../DataTable";

export default function Routing() {
  const { batches, partners, dispatches, dispatchSurplus } = useStore();
  const [f, setF] = useState({ batchId: "", channel: "ngo", partnerId: "", qty: "" });
  const [error, setError] = useState(null);
  const stock = fefoSort(batches.filter((b) => b.qty > 0 && daysToExpiry(b.expiry) <= 3));
  const options = partners.filter((p) => p.channel === f.channel);
  const set = (k) => (e) => { setF((s) => ({ ...s, [k]: e.target.value, ...(k === "channel" ? { partnerId: "" } : {}) })); setError(null); };

  const submit = (e) => {
    e.preventDefault();
    const res = dispatchSurplus({ ...f, batchId: Number(f.batchId) || null });
    if (!res.ok) return setError(res.error);
    setF({ batchId: "", channel: f.channel, partnerId: "", qty: "" });
  };

  return (
    <>
      <PageHeader title="Secondary Routing" subtitle="Divert unsold surplus to food banks, B2B buyers or composting — never landfill." />
      <div className="grid gap-6 lg:grid-cols-5">
        <Card title="New dispatch" className="lg:col-span-2">
          <form onSubmit={submit} className="space-y-4" data-testid="routing-form">
            <label className="block text-sm font-medium text-slate-700">Batch
              <select className={`${inputCls} mt-1`} value={f.batchId} onChange={set("batchId")} data-testid="route-batch">
                <option value="">Select batch…</option>
                {stock.map((b) => <option key={b.id} value={b.id}>{b.batchNo} — {b.product} ({b.qty} left)</option>)}
              </select>
            </label>
            <fieldset>
              <legend className="text-sm font-medium text-slate-700">Channel</legend>
              <div className="mt-1 grid grid-cols-3 gap-2">
                {CHANNELS.map((c) => (
                  <button type="button" key={c.id} data-testid={`channel-${c.id}`} onClick={() => set("channel")({ target: { value: c.id } })} className={`rounded-lg border px-2 py-2 text-xs font-semibold ${f.channel === c.id ? "border-emerald-600 bg-emerald-50 text-emerald-800" : "border-slate-300 text-slate-600"}`}>{c.label}</button>
                ))}
              </div>
            </fieldset>
            <label className="block text-sm font-medium text-slate-700">Partner
              <select className={`${inputCls} mt-1`} value={f.partnerId} onChange={set("partnerId")} data-testid="route-partner">
                <option value="">Select partner…</option>
                {options.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-700">Quantity (units)
              <input className={`${inputCls} mt-1`} type="text" inputMode="numeric" value={f.qty} onChange={set("qty")} data-testid="route-qty" placeholder="e.g. 20" />
            </label>
            <FormError>{error}</FormError>
            <Button type="submit" className="w-full" data-testid="route-submit"><Send size={16} /> Dispatch surplus</Button>
          </form>
        </Card>
        <Card title="Dispatch history" className="lg:col-span-3">
          <DataTable testid="dispatch-table" rows={dispatches} empty="No dispatches yet."
            columns={[
              { key: "id", header: "ID", className: "font-mono" },
              { key: "product", header: "Product" },
              { key: "qty", header: "Qty" },
              { key: "kg", header: "kg" },
              { key: "partner", header: "Partner" },
            ]} />
        </Card>
      </div>
    </>
  );
}
