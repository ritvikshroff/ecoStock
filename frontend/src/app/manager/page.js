"use client";
import { useState } from "react";
import { LayoutDashboard, Boxes, Tags, Share2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import Overview from "@/components/manager/Overview";
import Inventory from "@/components/manager/Inventory";
import Pricing from "@/components/manager/Pricing";
import Routing from "@/components/manager/Routing";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "inventory", label: "Inventory (FEFO)", icon: Boxes },
  { id: "pricing", label: "Dynamic Pricing", icon: Tags },
  { id: "routing", label: "Secondary Routing", icon: Share2 },
];
const VIEWS = { overview: Overview, inventory: Inventory, pricing: Pricing, routing: Routing };

export default function ManagerPage() {
  const [tab, setTab] = useState("overview");
  const View = VIEWS[tab];
  return <AppShell role="manager" tabs={TABS} tab={tab} setTab={setTab}><View /></AppShell>;
}
