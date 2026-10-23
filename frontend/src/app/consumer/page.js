"use client";
import { useState } from "react";
import { Store, Sprout, ClipboardList } from "lucide-react";
import AppShell from "@/components/AppShell";
import GreenShelf from "@/components/consumer/GreenShelf";
import Impact from "@/components/consumer/Impact";
import Reservations from "@/components/consumer/Reservations";

const TABS = [
  { id: "shelf", label: "Green Shelf", icon: Store },
  { id: "reservations", label: "My Reservations", icon: ClipboardList },
  { id: "impact", label: "My Impact", icon: Sprout },
];
const VIEWS = { shelf: GreenShelf, reservations: Reservations, impact: Impact };

export default function ConsumerPage() {
  const [tab, setTab] = useState("shelf");
  const View = VIEWS[tab];
  return <AppShell role="consumer" tabs={TABS} tab={tab} setTab={setTab}><View /></AppShell>;
}
