"use client";
import { useState } from "react";
import { MapPin, Clock, ShoppingBag, Search } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { daysToExpiry, fefoSort, money } from "@/lib/logic";
import { Button, EmptyState, FormError, Modal, PageHeader, inputCls } from "../ui";

export default function GreenShelf() {
  const { batches, reserve } = useStore();
  const [q, setQ] = useState("");
  const [item, setItem] = useState(null);
  const [qty, setQty] = useState(1);
  const [error, setError] = useState(null);
  const items = fefoSort(batches.filter((b) => b.discountPct > 0 && b.qty > 0 && daysToExpiry(b.expiry) >= 0))
    .filter((b) => `${b.product} ${b.store}`.toLowerCase().includes(q.toLowerCase()));

  const open = (b) => { setItem(b); setQty(1); setError(null); };
  const confirm = () => {
    const res = reserve(item.id, qty);
    if (!res.ok) return setError(res.error);
    setItem(null);
  };

  return (
    <>
      <PageHeader title="Green Shelf" subtitle="Fresh food nearing its date, at up to half price, from stores near you." />
      <div className="relative mb-5 max-w-sm">
        <Search size={16} className="absolute left-3 top-3 text-slate-400" />
        <input className={`${inputCls} pl-9`} placeholder="Search items or stores…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="shelf-search" />
      </div>
      {items.length === 0 ? <EmptyState text="No bargains match right now. Check back soon!" /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="shelf-grid">
          {items.map((b) => {
            const d = daysToExpiry(b.expiry);
            return (
              <article key={b.id} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm" data-testid="shelf-card" data-batch={b.batchNo}>
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-slate-900">{b.product}</h3>
                  <span className="rounded-full bg-emerald-600 px-2.5 py-0.5 text-xs font-bold text-white" data-testid="discount-chip">{b.discountPct}% OFF</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{b.category}</p>
                <p className="mt-3 text-2xl font-bold text-emerald-700"><span data-testid="card-price">{money(b.discountedPrice)}</span> <s className="text-sm font-normal text-slate-400">{money(b.price)}</s></p>
                <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-600"><Clock size={13} /> {d === 0 ? "Use today" : `${d} day${d > 1 ? "s" : ""} left`} · {b.qty} available</p>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-600"><MapPin size={13} /> {b.store} · {b.distanceKm} km</p>
                <Button className="mt-4" onClick={() => open(b)} data-testid="reserve-btn"><ShoppingBag size={16} /> Reserve for pickup</Button>
              </article>
            );
          })}
        </div>
      )}
      <Modal open={!!item} title={`Reserve ${item?.product}`} onClose={() => setItem(null)} testid="reserve-modal">
        {item && (
          <>
            <label className="block text-sm font-medium text-slate-700">Quantity (max {item.qty})
              <input className={`${inputCls} mt-1`} type="text" inputMode="numeric" value={qty} onChange={(e) => { setQty(e.target.value); setError(null); }} data-testid="reserve-qty" />
            </label>
            <p className="mt-3 text-sm text-slate-600">Total: <b data-testid="reserve-total">{money((Number(qty) > 0 ? Number(qty) : 0) * item.discountedPrice)}</b> · Pay in store at pickup.</p>
            <FormError>{error}</FormError>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setItem(null)}>Cancel</Button>
              <Button onClick={confirm} data-testid="reserve-confirm">Confirm reservation</Button>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
