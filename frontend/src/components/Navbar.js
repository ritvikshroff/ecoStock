"use client";
import Link from "next/link";
import { Menu, Wifi, WifiOff } from "lucide-react";
import { ROLES } from "@/lib/roles";
import { useStore } from "@/context/StoreContext";

export default function Navbar({ role, onMenu }) {
  const { apiOnline } = useStore();
  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur" data-testid="navbar">
      <button className="rounded p-2 hover:bg-slate-100 lg:hidden" onClick={onMenu} aria-label="Toggle menu" data-testid="menu-toggle"><Menu size={20} /></button>
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1" role="tablist" aria-label="Switch role">
        {ROLES.map(({ id, label, href, icon: Icon }) => (
          <Link
            key={id}
            href={href}
            data-testid={`role-${id}`}
            aria-selected={role === id}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium ${role === id ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
          >
            <Icon size={16} /> <span className="hidden sm:inline">{label}</span>
          </Link>
        ))}
      </div>
      <div className="ml-auto flex items-center gap-1.5 text-xs text-slate-500" data-testid="api-status" title="Backend REST API status">
        {apiOnline ? <Wifi size={14} className="text-emerald-600" /> : <WifiOff size={14} className="text-amber-600" />}
        {apiOnline ? "API connected" : "Mock data mode"}
      </div>
    </header>
  );
}
