"use client";
import { useState } from "react";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import { Toasts } from "./ui";

export default function AppShell({ role, tabs, tab, setTab, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar role={role} tabs={tabs} tab={tab} onSelect={(t) => { setTab(t); setOpen(false); }} open={open} />
      <div className="lg:pl-64">
        <Navbar role={role} onMenu={() => setOpen((o) => !o)} />
        <main className="mx-auto max-w-6xl p-4 sm:p-6" data-testid={`view-${tab}`}>{children}</main>
      </div>
      <Toasts />
    </div>
  );
}
