"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import * as logic from "@/lib/logic";
import { PARTNERS, seedBatches, seedImpact, seedLots } from "@/lib/mockData";

const Ctx = createContext(null);
export const useStore = () => useContext(Ctx);

const ESL_SYNC_MS = 1200;

export function StoreProvider({ children }) {
  const [batches, setBatches] = useState(seedBatches);
  const [lots, setLots] = useState(seedLots);
  const [dispatches, setDispatches] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [bids, setBids] = useState([]);
  const [manifests, setManifests] = useState([]);
  const [impact, setImpact] = useState(seedImpact);
  const [sync, setSync] = useState({}); // batchId -> "syncing" | "synced"
  const [toasts, setToasts] = useState([]);
  const [apiOnline, setApiOnline] = useState(false);
  const [revenue, setRevenue] = useState({ list: 480, recovered: 312 });
  const [dispatchedKg, setDispatchedKg] = useState(42);
  const seq = useRef(1);

  useEffect(() => {
    api.ping().then((r) => setApiOnline(r.ok));
  }, []);

  const toast = useCallback((message, tone = "success") => {
    const id = seq.current++;
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);

  // ---- Manager actions ----
  const applyMarkdown = useCallback(
    (ids, pct) => {
      if (!ids.length) return { ok: false, error: "Select at least one batch." };
      let err = null;
      try { logic.markdownPrice(1, pct); } catch (e) { err = e.message; }
      if (err) return { ok: false, error: err };
      setBatches((bs) =>
        bs.map((b) => (ids.includes(b.id) ? { ...b, discountPct: pct, discountedPrice: logic.markdownPrice(b.price, pct) } : b))
      );
      setSync((s) => ({ ...s, ...Object.fromEntries(ids.map((i) => [i, "syncing"])) }));
      setTimeout(() => setSync((s) => ({ ...s, ...Object.fromEntries(ids.map((i) => [i, "synced"])) })), ESL_SYNC_MS);
      api.applyMarkdown(ids, pct);
      toast(`${pct}% markdown applied to ${ids.length} batch(es). Syncing POS & ESL...`);
      return { ok: true };
    },
    [toast]
  );

  const dispatchSurplus = useCallback(
    ({ batchId, channel, partnerId, qty }) => {
      const batch = batches.find((b) => b.id === batchId);
      const error = logic.validateDispatch({ batch, qty, partnerId, channel });
      if (error) return { ok: false, error };
      const n = Number(qty);
      const partner = PARTNERS.find((p) => p.id === partnerId);
      const kg = Math.round(n * batch.unitKg * 10) / 10;
      const id = `D-${5000 + dispatches.length + 1}`;
      setBatches((bs) => bs.map((b) => (b.id === batchId ? { ...b, qty: b.qty - n } : b)));
      setDispatches((d) => [{ id, batchNo: batch.batchNo, product: batch.product, channel, partner: partner.name, qty: n, kg, at: new Date().toISOString() }, ...d]);
      setDispatchedKg((k) => k + kg);
      if (channel !== "compost") {
        setLots((l) => [
          { id: `L-${id}`, title: `${batch.product} (${batch.batchNo})`, type: channel === "ngo" ? "donation" : "wholesale", kg, units: n, expiry: batch.expiry, reserve: channel === "b2b" ? Math.round(kg * 2) : 0, origin: batch.store, status: "open", counted: true },
          ...l,
        ]);
      }
      api.dispatchSurplus({ batch_id: batchId, channel, partner_id: partnerId, quantity: n });
      toast(`Routed ${n} x ${batch.product} to ${partner.name}.`);
      return { ok: true };
    },
    [batches, dispatches.length, toast]
  );

  // ---- Consumer actions ----
  const reserve = useCallback(
    (batchId, qty) => {
      const batch = batches.find((b) => b.id === batchId);
      const n = Number(qty);
      if (!batch || !(batch.discountPct > 0)) return { ok: false, error: "Item is not on the Green Shelf." };
      if (!Number.isInteger(n) || n < 1) return { ok: false, error: "Choose at least 1 item." };
      if (n > batch.qty) return { ok: false, error: `Only ${batch.qty} left.` };
      const kg = Math.round(n * batch.unitKg * 10) / 10;
      const total = Math.round(n * batch.discountedPrice * 100) / 100;
      const code = `ECO-${1000 + reservations.length + 1}`;
      setBatches((bs) => bs.map((b) => (b.id === batchId ? { ...b, qty: b.qty - n } : b)));
      setReservations((r) => [{ code, batchId, product: batch.product, store: batch.store, qty: n, total, kg, status: "Reserved" }, ...r]);
      setImpact((i) => ({ itemsRescued: i.itemsRescued + n, kgSaved: Math.round((i.kgSaved + kg) * 10) / 10, moneySaved: Math.round((i.moneySaved + n * (batch.price - batch.discountedPrice)) * 100) / 100 }));
      setRevenue((r) => ({ list: r.list + n * batch.price, recovered: r.recovered + total }));
      api.createOrder({ batch_id: batchId, quantity: n });
      toast(`Reserved! Pickup code ${code}.`);
      return { ok: true, code };
    },
    [batches, reservations.length, toast]
  );

  const cancelReservation = useCallback((code) => {
    const r = reservations.find((x) => x.code === code);
    if (!r || r.status !== "Reserved") return;
    setReservations((rs) => rs.map((x) => (x.code === code ? { ...x, status: "Cancelled" } : x)));
    setBatches((bs) => bs.map((b) => (b.id === r.batchId ? { ...b, qty: b.qty + r.qty } : b)));
    setImpact((i) => ({ ...i, itemsRescued: i.itemsRescued - r.qty, kgSaved: Math.round((i.kgSaved - r.kg) * 10) / 10 }));
    toast(`Reservation ${code} cancelled.`, "info");
  }, [reservations, toast]);

  const markPickedUp = useCallback((code) => {
    setReservations((rs) => rs.map((x) => (x.code === code && x.status === "Reserved" ? { ...x, status: "Picked up" } : x)));
  }, []);

  // ---- Partner actions ----
  const submitBid = useCallback(
    (lotId, amount, bidder) => {
      const lot = lots.find((l) => l.id === lotId);
      const n = Number(amount);
      if (!lot || lot.type !== "wholesale") return { ok: false, error: "Bids apply to wholesale lots only." };
      if (!(n > 0)) return { ok: false, error: "Enter a bid amount greater than 0." };
      if (n < lot.reserve) return { ok: false, error: `Bid must meet the reserve price of $${lot.reserve}.` };
      setBids((b) => [{ id: `BID-${b.length + 1}`, lotId, title: lot.title, amount: n, bidder, status: "Pending" }, ...b]);
      toast(`Bid of $${n} submitted for ${lot.title}.`);
      return { ok: true };
    },
    [lots, toast]
  );

  const makeManifest = useCallback((lot, partnerName, kind, amount = 0) => {
    const slot = new Date(Date.now() + 86400000);
    setLots((l) => l.map((x) => (x.id === lot.id ? { ...x, status: "allocated" } : x)));
    setManifests((m) => [
      { id: `MAN-${7000 + m.length + 1}`, lotId: lot.id, title: lot.title, kg: lot.kg, units: lot.units, partner: partnerName, kind, amount, pickup: `${logic.toISODate(slot)} 09:00-11:00`, origin: lot.origin, counted: !!lot.counted, status: "Scheduled" },
      ...m,
    ]);
  }, []);

  const acceptBid = useCallback((bidId) => {
    const bid = bids.find((b) => b.id === bidId);
    const lot = bid && lots.find((l) => l.id === bid.lotId);
    if (!lot || lot.status !== "open") return;
    setBids((bs) => bs.map((b) => (b.id === bidId ? { ...b, status: "Won" } : b.lotId === bid.lotId ? { ...b, status: "Outbid" } : b)));
    makeManifest(lot, bid.bidder, "Wholesale", bid.amount);
    toast(`Bid ${bidId} accepted. Manifest generated.`);
  }, [bids, lots, makeManifest, toast]);

  const claimDonation = useCallback(
    (lotId, ngoName) => {
      const lot = lots.find((l) => l.id === lotId);
      if (!lot || lot.type !== "donation" || lot.status !== "open") return { ok: false, error: "Lot is no longer available." };
      makeManifest(lot, ngoName, "Donation");
      toast(`Dispatch accepted. Manifest generated for ${lot.title}.`);
      return { ok: true };
    },
    [lots, makeManifest, toast]
  );

  const confirmReceipt = useCallback((id) => {
    const m = manifests.find((x) => x.id === id);
    if (!m || m.status === "Received") return;
    setManifests((ms) => ms.map((x) => (x.id === id ? { ...x, status: "Received", receivedAt: new Date().toISOString() } : x)));
    if (!m.counted) setDispatchedKg((k) => k + m.kg);
    toast(`Receipt confirmed for ${id}.`);
  }, [manifests, toast]);

  const state = useMemo(
    () => ({ batches, lots, dispatches, reservations, bids, manifests, impact, sync, revenue, dispatchedKg }),
    [batches, lots, dispatches, reservations, bids, manifests, impact, sync, revenue, dispatchedKg]
  );

  // Test/debug introspection hook used by the white-box Selenium suite.
  useEffect(() => {
    window.__ECOSTOCK__ = { state, logic };
  }, [state]);

  const value = {
    ...state, toasts, apiOnline, partners: PARTNERS,
    applyMarkdown, dispatchSurplus, reserve, cancelReservation, markPickedUp,
    submitBid, acceptBid, claimDonation, confirmReceipt, toast,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
