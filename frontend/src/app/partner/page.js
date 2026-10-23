"use client";
import { useState } from "react";
import { PackageSearch, Gavel, FileCheck2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import Catalog from "@/components/partner/Catalog";
import Bids from "@/components/partner/Bids";
import Manifests from "@/components/partner/Manifests";

const TABS = [
  { id: "catalog", label: "Surplus Catalog", icon: PackageSearch },
  { id: "bids", label: "Bids", icon: Gavel },
  { id: "manifests", label: "Pickup Manifests", icon: FileCheck2 },
];
const VIEWS = { catalog: Catalog, bids: Bids, manifests: Manifests };
const PERSONAS = [
  { id: "b2b-1", kind: "b2b", name: "FreshFlip Wholesale" },
  { id: "ngo-1", kind: "ngo", name: "City Food Bank" },
];

export default function PartnerPage() {
  const [tab, setTab] = useState("catalog");
  const [pid, setPid] = useState("b2b-1");
  const persona = PERSONAS.find((p) => p.id === pid);
  const View = VIEWS[tab];
  return (
    <AppShell role="partner" tabs={TABS} tab={tab} setTab={setTab}>
      <div className="mb-5 flex items-center gap-2 text-sm">
        <label htmlFor="persona" className="font-medium text-slate-600">Signed in as</label>
        <select id="persona" value={pid} onChange={(e) => setPid(e.target.value)} data-testid="persona-select" className="rounded-lg border border-slate-300 bg-white px-3 py-1.5">
          {PERSONAS.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.kind.toUpperCase()})</option>)}
        </select>
      </div>
      <View persona={persona} />
    </AppShell>
  );
}
