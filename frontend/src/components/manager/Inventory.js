"use client";
import { useStore } from "@/context/StoreContext";
import { batchStatus, daysToExpiry, fefoSort } from "@/lib/logic";
import { Badge, Card, PageHeader } from "../ui";
import DataTable from "../DataTable";

export default function Inventory() {
  const { batches } = useStore();
  const rows = fefoSort(batches.filter((b) => b.qty > 0)).map((b, i) => ({ ...b, rank: i + 1 }));
  const columns = [
    { key: "rank", header: "FEFO #" },
    { key: "batchNo", header: "Batch", className: "font-mono" },
    { key: "product", header: "Product", className: "font-medium text-slate-900" },
    { key: "qty", header: "Qty" },
    { key: "expiry", header: "Expiry" },
    { key: "days", header: "Days left", render: (r) => daysToExpiry(r.expiry) },
    { key: "status", header: "Status", render: (r) => <Badge>{batchStatus(r)}</Badge> },
  ];
  return (
    <>
      <PageHeader title="Inventory (FEFO)" subtitle="First-Expired, First-Out: earliest expiry is always at the top." />
      <Card><DataTable testid="inventory-table" columns={columns} rows={rows} empty="No stock on hand." /></Card>
    </>
  );
}
