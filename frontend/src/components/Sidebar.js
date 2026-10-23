"use client";
import Link from "next/link";
import { Leaf } from "lucide-react";

export default function Sidebar({ role, tabs, tab, onSelect, open }) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-emerald-900/20 bg-emerald-950 text-emerald-50 transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      data-testid="sidebar"
    >
      <Link href="/" className="flex items-center gap-2 px-6 py-5 text-lg font-bold" data-testid="brand">
        <Leaf className="text-emerald-400" /> ecoStock
      </Link>
      <p className="px-6 pb-2 text-xs uppercase tracking-wider text-emerald-300/70" data-testid="role-label">{role}</p>
      <nav className="space-y-1 px-3">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onSelect(id)}
            data-testid={`nav-${id}`}
            aria-current={tab === id ? "page" : undefined}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${tab === id ? "bg-emerald-600 text-white" : "text-emerald-100 hover:bg-emerald-900"}`}
          >
            <Icon size={18} /> {label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
