"use client";
import { useStore } from "@/context/StoreContext";
import { Badge, Button, Card, PageHeader } from "../ui";
import DataTable from "../DataTable";
import { money } from "@/lib/logic";

const TONE = { Reserved: "bg-sky-100 text-sky-800", "Picked up": "bg-emerald-100 text-emerald-800", Cancelled: "bg-slate-200 text-slate-600" };

export default function Reservations() {
  const { reservations, cancelReservation, markPickedUp } = useStore();
  return (
    <>
      <PageHeader title="My Reservations" subtitle="Show your pickup code at the customer service desk." />
      <Card>
        <DataTable testid="reservation-table" rowKey="code" rows={reservations} empty="No reservations yet. Visit the Green Shelf to grab a bargain."
          columns={[
            { key: "code", header: "Pickup code", className: "font-mono font-bold" },
            { key: "product", header: "Item" },
            { key: "qty", header: "Qty" },
            { key: "total", header: "Total", render: (r) => money(r.total) },
            { key: "store", header: "Store" },
            { key: "status", header: "Status", render: (r) => <Badge tone={TONE[r.status]}>{r.status}</Badge> },
            { key: "act", header: "", render: (r) => r.status === "Reserved" && (
              <span className="flex gap-2">
                <Button variant="outline" className="!px-2 !py-1" onClick={() => markPickedUp(r.code)} data-testid={`pickup-${r.code}`}>Picked up</Button>
                <Button variant="outline" className="!px-2 !py-1" onClick={() => cancelReservation(r.code)} data-testid={`cancel-${r.code}`}>Cancel</Button>
              </span>) },
          ]} />
      </Card>
    </>
  );
}
