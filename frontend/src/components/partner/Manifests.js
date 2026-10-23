"use client";
import { useState } from "react";
import { FileText, PackageCheck } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { Badge, Button, Card, Modal, PageHeader } from "../ui";
import DataTable from "../DataTable";
import { money } from "@/lib/logic";

export default function Manifests({ persona }) {
  const { manifests, confirmReceipt } = useStore();
  const [view, setView] = useState(null);
  const mine = manifests.filter((m) => m.partner === persona.name);
  return (
    <>
      <PageHeader title="Pickup Manifests" subtitle="Official pickup schedules. Confirm receipt once the shipment arrives." />
      <Card>
        <DataTable testid="manifest-table" rows={mine} empty="No scheduled pickups yet."
          columns={[
            { key: "id", header: "Manifest", className: "font-mono" },
            { key: "title", header: "Lot" },
            { key: "kind", header: "Type" },
            { key: "pickup", header: "Pickup window" },
            { key: "origin", header: "Origin" },
            { key: "status", header: "Status", render: (r) => <Badge tone={r.status === "Received" ? "bg-emerald-100 text-emerald-800" : "bg-sky-100 text-sky-800"}>{r.status}</Badge> },
            { key: "act", header: "", render: (r) => (
              <span className="flex gap-2">
                <Button variant="outline" className="!px-2 !py-1" onClick={() => setView(r)} data-testid={`view-${r.id}`}><FileText size={14} /> View</Button>
                {r.status !== "Received" && <Button className="!px-2 !py-1" onClick={() => confirmReceipt(r.id)} data-testid={`confirm-${r.id}`}><PackageCheck size={14} /> Confirm receipt</Button>}
              </span>) },
          ]} />
      </Card>
      <Modal open={!!view} title={`Manifest ${view?.id}`} onClose={() => setView(null)} testid="manifest-modal">
        {view && (
          <dl className="grid grid-cols-2 gap-y-2 text-sm" data-testid="manifest-detail">
            <dt className="text-slate-500">Lot</dt><dd>{view.title}</dd>
            <dt className="text-slate-500">Weight</dt><dd>{view.kg} kg / {view.units} units</dd>
            <dt className="text-slate-500">Origin</dt><dd>{view.origin}</dd>
            <dt className="text-slate-500">Recipient</dt><dd>{view.partner}</dd>
            <dt className="text-slate-500">Pickup</dt><dd>{view.pickup}</dd>
            <dt className="text-slate-500">Value</dt><dd>{view.kind === "Donation" ? "Donation (tax receipt)" : money(view.amount)}</dd>
          </dl>
        )}
      </Modal>
    </>
  );
}
