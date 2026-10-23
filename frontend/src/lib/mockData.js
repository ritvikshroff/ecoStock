import { addDays } from "./logic";

const today = () => new Date();

// [batchNo, product, category, qty, unitKg, price, expiryOffsetDays, discountPct]
const BATCH_ROWS = [
  ["B-1001", "Whole Milk 1L", "Dairy", 60, 1.0, 68, 1, 0],
  ["B-1002", "Greek Yogurt 500g", "Dairy", 45, 0.5, 120, 2, 20],
  ["B-1003", "Sourdough Loaf", "Bakery", 30, 0.7, 180, 0, 0],
  ["B-1004", "Chicken Breast 1kg", "Meat", 24, 1.0, 320, 3, 0],
  ["B-1005", "Baby Spinach 200g", "Produce", 80, 0.2, 60, 2, 0],
  ["B-1006", "Strawberries 400g", "Produce", 50, 0.4, 180, 1, 35],
  ["B-1007", "Cheddar Block 400g", "Dairy", 40, 0.4, 260, 9, 0],
  ["B-1008", "Atlantic Salmon 300g", "Seafood", 18, 0.3, 750, 3, 0],
  ["B-1009", "Orange Juice 1.5L", "Beverages", 70, 1.5, 150, 14, 0],
  ["B-1010", "Hummus 250g", "Deli", 55, 0.25, 140, 5, 0],
  ["B-1011", "Bananas 1kg", "Produce", 90, 1.0, 60, 2, 0],
  ["B-1012", "Pasta Penne 500g", "Pantry", 120, 0.5, 95, 120, 0],
];

export function seedBatches() {
  return BATCH_ROWS.map(([batchNo, product, category, qty, unitKg, price, off, discountPct], i) => ({
    id: i + 1,
    batchNo,
    product,
    category,
    qty,
    initialQty: qty,
    unitKg,
    price,
    expiry: addDays(today(), off),
    discountPct,
    discountedPrice: discountPct ? Math.round(price * (1 - discountPct / 100) * 100) / 100 : null,
    store: i % 2 === 0 ? "Green Market Downtown" : "Green Market Riverside",
    distanceKm: i % 2 === 0 ? 0.8 : 2.4,
  }));
}

export const PARTNERS = [
  { id: "ngo-1", name: "City Food Bank", channel: "ngo" },
  { id: "ngo-2", name: "Hope Kitchen NGO", channel: "ngo" },
  { id: "b2b-1", name: "FreshFlip Wholesale", channel: "b2b" },
  { id: "b2b-2", name: "BulkBridge Traders", channel: "b2b" },
  { id: "compost-1", name: "GreenCycle Composting", channel: "compost" },
];

export const CHANNELS = [
  { id: "ngo", label: "NGO Food Bank", hint: "Donation, tax receipt issued" },
  { id: "b2b", label: "B2B Buyer", hint: "Wholesale liquidation" },
  { id: "compost", label: "Composting", hint: "Last resort, zero landfill" },
];

export function seedLots() {
  return [
    { id: "L-9001", title: "Mixed Produce Pallet", type: "wholesale", kg: 320, units: 400, expiry: addDays(today(), 2), reserve: 15000, origin: "Green Market Downtown", status: "open" },
    { id: "L-9002", title: "Dairy Crate Assortment", type: "wholesale", kg: 210, units: 260, expiry: addDays(today(), 3), reserve: 12000, origin: "Green Market Riverside", status: "open" },
    { id: "L-9003", title: "Bakery Surplus Trays", type: "donation", kg: 95, units: 140, expiry: addDays(today(), 1), reserve: 0, origin: "Green Market Downtown", status: "open" },
    { id: "L-9004", title: "Fresh Vegetables Box Set", type: "donation", kg: 150, units: 200, expiry: addDays(today(), 2), reserve: 0, origin: "Green Market Riverside", status: "open" },
  ];
}

export function seedImpact() {
  return { itemsRescued: 14, kgSaved: 9.6, moneySaved: 1450 };
}
