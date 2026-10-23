"use client";
import { useState } from "react";
import { Gavel, HeartHandshake } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { daysToExpiry, money } from "@/lib/logic";
import { Badge, Button, Card, FormError, Modal, PageHeader, inputCls } from "../ui";
import DataTable from "../DataTable";

export default function Catalog({ persona }) {
  const { lots, submitBid, claimDonation } = useStore();
  const [filter, setFilter] = useState("all");
  const [bidLot, setBidLot] = useState(null);
  const [amount, setAmount] = useState("");
  const [error, setError] = useState(null);
  const rows = lots.filter((l) => l.status === "open" && (filter === "all" || l.type === filter));

  const place = () => {
    const res = submitBid(bidLot.id, amount, persona.name);
    if (!res.ok) return setError(res.error);
    setBidLot(null); setAmount("");
  };

  const columns = [
    { key: "id", header: "Lot", className: "font-mono" },
    { key: "title", header: "Contents", className: "font-medium text-slate-900" },
    { key: "type", header: "Category", render: (r) => <Badge tone={r.type === "donation" ? "bg-rose-100 text-rose-800" : "bg-indigo-100 text-indigo-800"}>{r.type === "donation" ? "Charitable donation" : "Wholesale"}</Badge> },
    { key: "kg", header: "Weight", render: (r) => `${r.kg} kg` },
    { key: "expiry", header: "Expires", render: (r) => `${r.expiry} (${daysToExpiry(r.expiry)}d)` },
    { key: "reserve", header: "Reserve", render: (r) => (r.type === "wholesale" ? money(r.reserve) : "Free") },
    { key: "act", header: "", render: (r) => r.type === "wholesale"
      ? <Button className="!px-3 !py-1" disabled={persona.kind !== "b2b"} title={persona.kind !== "b2b" ? "Switch to a B2B account to bid" : ""} onClick={() => { setBidLot(r); setError(null); }} data-testid={`bid-${r.id}`}><Gavel size={14} /> Bid</Button>
      : <Button className="!px-3 !py-1" disabled={persona.kind !== "ngo"} title={persona.kind !== "ngo" ? "Switch to an NGO account to claim" : ""} onClick={() => claimDonation(r.id, persona.name)} data-testid={`claim-${r.id}`}><HeartHandshake size={14} /> Accept dispatch</Button> },
  ];

  return (
    <>
      <PageHeader title="Bulk Surplus Catalog" subtitle="Near-expiry lots released for wholesale liquidation or charitable donation." />
      <Card title={`Open lots (${rows.length})`} action={
        <div className="flex gap-1" role="group" aria-label="Filter lots">
          {[["all", "All"], ["wholesale", "Wholesale"], ["donation", "Donation"]].map(([id, l]) => (
            <button key={id} onClick={() => setFilter(id)} data-testid={`filter-${id}`} className={`rounded-md px-3 py-1 text-sm font-medium ${filter === id ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-700"}`}>{l}</button>
          ))}
        </div>}>
        <DataTable testid="catalog-table" columns={columns} rows={rows} empty="No open lots in this category." />
      </Card>
      <Modal open={!!bidLot} title={`Bid on ${bidLot?.title}`} onClose={() => setBidLot(null)} testid="bid-modal">
        {bidLot && (<>
          <p className="text-sm text-slate-600">Reserve price: <b>{money(bidLot.reserve)}</b> · {bidLot.kg} kg</p>
          <label className="mt-3 block text-sm font-medium text-slate-700">Your bid (USD)
            <input className={`${inputCls} mt-1`} type="text" inputMode="decimal" value={amount} onChange={(e) => { setAmount(e.target.value); setError(null); }} data-testid="bid-amount" />
          </label>
          <FormError>{error}</FormError>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setBidLot(null)}>Cancel</Button>
            <Button onClick={place} data-testid="bid-submit">Submit bid</Button>
          </div>
        </>)}
      </Modal>
    </>
  );
}
