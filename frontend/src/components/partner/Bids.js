"use client";
import { useStore } from "@/context/StoreContext";
import { Badge, Button, Card, PageHeader } from "../ui";
import DataTable from "../DataTable";
import { money } from "@/lib/logic";

const TONE = { Pending: "bg-amber-100 text-amber-800", Won: "bg-emerald-100 text-emerald-800", Outbid: "bg-slate-200 text-slate-600" };

export default function Bids({ persona }) {
  const { bids, acceptBid } = useStore();
  const mine = bids.filter((b) => b.bidder === persona.name);
  return (
    <>
      <PageHeader title="My Bids & Claims" subtitle="Track wholesale bids placed from this account." />
      <Card>
        <DataTable testid="bids-table" rows={mine} empty="No bids yet. Browse the catalog to place one."
          columns={[
            { key: "id", header: "Bid", className: "font-mono" },
            { key: "title", header: "Lot" },
            { key: "amount", header: "Amount", render: (r) => money(r.amount) },
            { key: "status", header: "Status", render: (r) => <Badge tone={TONE[r.status]}>{r.status}</Badge> },
            { key: "act", header: "", render: (r) => r.status === "Pending" && <Button variant="outline" className="!px-2 !py-1" onClick={() => acceptBid(r.id)} data-testid={`accept-${r.id}`}>Simulate store acceptance (demo)</Button> },
          ]} />
      </Card>
    </>
  );
}
