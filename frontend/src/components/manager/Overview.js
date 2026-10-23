"use client";
import { Boxes, Tag, Recycle, TrendingUp } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { computeKpis, co2Saved, money } from "@/lib/logic";
import { KpiCard, Card, PageHeader } from "../ui";

export default function Overview() {
  const { batches, dispatchedKg, impact, revenue, dispatches } = useStore();
  const k = computeKpis({ batches, dispatchedKg, soldKg: impact.kgSaved, recoveredRevenue: revenue.recovered, listRevenue: revenue.list });
  return (
    <>
      <PageHeader title="Store Overview" subtitle="Live zero-waste performance across your stores." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard id="active-batches" icon={Boxes} label="Active batches" value={k.activeBatches} sub="Batches with stock on hand" />
        <KpiCard id="items-discounted" icon={Tag} label="Items discounted" value={k.itemsDiscounted} sub="Units currently on markdown" tone="amber" />
        <KpiCard id="waste-diverted" icon={Recycle} label="Landfill diverted" value={`${k.wasteDivertedKg} kg`} sub={`≈ ${co2Saved(k.wasteDivertedKg)} kg CO₂e avoided`} tone="sky" />
        <KpiCard id="revenue-recovery" icon={TrendingUp} label="Revenue recovery" value={`${k.recoveryPct}%`} sub={`${money(revenue.recovered)} of ${money(revenue.list)} list value`} tone="violet" />
      </div>
      <Card title="Recent routing activity" className="mt-6">
        {dispatches.length === 0 ? (
          <p className="text-sm text-slate-500" data-testid="no-activity">No surplus routed yet. Use Secondary Routing to divert stock.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm" data-testid="activity-list">
            {dispatches.slice(0, 5).map((d) => (
              <li key={d.id} className="flex justify-between py-2"><span>{d.qty} × {d.product} → {d.partner}</span><span className="text-slate-500">{d.kg} kg</span></li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
