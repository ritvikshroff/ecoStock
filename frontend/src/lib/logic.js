// Pure business logic. No React, no I/O -> trivially testable (white-box tests target these).

export const NEAR_EXPIRY_DAYS = 3;
export const MARKDOWN_TIERS = [20, 35, 50];
export const CO2_PER_KG_FOOD = 2.5; // kg CO2e avoided per kg of food kept out of landfill
const MS_DAY = 86400000;

export function toISODate(d) {
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function addDays(base, n) {
  const d = new Date(base);
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() + n);
  return toISODate(d);
}

export function daysToExpiry(expiry, today = new Date()) {
  const a = new Date(expiry + "T12:00:00");
  const b = new Date(toISODate(today) + "T12:00:00");
  return Math.round((a - b) / MS_DAY);
}

/** FEFO: earliest expiry first; ties broken by batch number so order is stable. */
export function fefoSort(batches) {
  return [...batches].sort(
    (x, y) => x.expiry.localeCompare(y.expiry) || x.batchNo.localeCompare(y.batchNo)
  );
}

export function batchStatus(b, today = new Date()) {
  if (b.qty <= 0) return "Cleared";
  const d = daysToExpiry(b.expiry, today);
  if (d < 0) return "Expired";
  if (b.discountPct > 0) return "Discounted";
  if (d <= 1) return "Critical";
  if (d <= NEAR_EXPIRY_DAYS) return "Near Expiry";
  return "Fresh";
}

export function isNearExpiry(b, today = new Date()) {
  const d = daysToExpiry(b.expiry, today);
  return b.qty > 0 && d >= 0 && d <= NEAR_EXPIRY_DAYS;
}

export function markdownPrice(price, pct) {
  if (!MARKDOWN_TIERS.includes(pct)) throw new Error(`Invalid markdown tier: ${pct}`);
  return Math.round(price * (1 - pct / 100) * 100) / 100;
}

export function validateDispatch({ batch, qty, partnerId, channel }) {
  if (!batch) return "Select a batch to route.";
  if (!channel) return "Select a channel.";
  if (!partnerId) return "Select a partner.";
  const n = Number(qty);
  if (!Number.isInteger(n) || n <= 0) return "Quantity must be a whole number greater than 0.";
  if (n > batch.qty) return `Only ${batch.qty} units available in ${batch.batchNo}.`;
  return null;
}

export function co2Saved(kg) {
  return Math.round(kg * CO2_PER_KG_FOOD * 100) / 100;
}

export function computeKpis({ batches, dispatchedKg, soldKg, recoveredRevenue, listRevenue }) {
  const active = batches.filter((b) => b.qty > 0);
  const discounted = active.filter((b) => b.discountPct > 0);
  const recoveryPct = listRevenue > 0 ? Math.round((recoveredRevenue / listRevenue) * 1000) / 10 : 0;
  return {
    activeBatches: active.length,
    itemsDiscounted: discounted.reduce((s, b) => s + b.qty, 0),
    wasteDivertedKg: Math.round((dispatchedKg + soldKg) * 10) / 10,
    recoveryPct,
  };
}

export const CURRENCY = "₹";
export const money = (n) =>
  `${CURRENCY}${Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
