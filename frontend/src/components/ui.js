"use client";
import { X, CheckCircle2, Info, AlertTriangle } from "lucide-react";
import { useStore } from "@/context/StoreContext";

export function KpiCard({ id, icon: Icon, label, value, sub, tone = "emerald" }) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    sky: "bg-sky-50 text-sky-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" data-testid={`kpi-${id}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`rounded-lg p-2 ${tones[tone]}`}><Icon size={18} /></span>
      </div>
      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900" data-testid={`kpi-${id}-value`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

const BADGE = {
  Fresh: "bg-emerald-100 text-emerald-800",
  "Near Expiry": "bg-amber-100 text-amber-800",
  Critical: "bg-red-100 text-red-800",
  Expired: "bg-slate-200 text-slate-700",
  Discounted: "bg-sky-100 text-sky-800",
  Cleared: "bg-slate-100 text-slate-500",
  default: "bg-slate-100 text-slate-700",
};
export function Badge({ children, tone }) {
  const cls = tone || BADGE[children] || BADGE.default;
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid="badge">{children}</span>;
}

export function Card({ title, action, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
          <h3 className="font-semibold text-slate-800">{title}</h3>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-900" data-testid="page-title">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}

export function Button({ variant = "primary", className = "", ...props }) {
  const v = {
    primary: "bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-300",
    outline: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50",
    danger: "bg-red-600 text-white hover:bg-red-700",
  }[variant];
  return <button type="button" className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed ${v} ${className}`} {...props} />;
}

export function Modal({ open, title, onClose, children, testid = "modal" }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" role="dialog" aria-modal="true" data-testid={testid}>
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <button aria-label="Close" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100" data-testid={`${testid}-close`}><X size={18} /></button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function FormError({ children }) {
  if (!children) return null;
  return <p role="alert" className="mt-2 flex items-center gap-1 text-sm text-red-600" data-testid="form-error"><AlertTriangle size={14} />{children}</p>;
}

export function EmptyState({ text }) {
  return <p className="py-10 text-center text-sm text-slate-500" data-testid="empty-state">{text}</p>;
}

export function Toasts() {
  const { toasts } = useStore();
  return (
    <div className="fixed bottom-4 right-4 z-[60] space-y-2" data-testid="toasts">
      {toasts.map((t) => (
        <div key={t.id} className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg" data-testid="toast">
          {t.tone === "info" ? <Info size={16} /> : <CheckCircle2 size={16} className="text-emerald-400" />}
          {t.message}
        </div>
      ))}
    </div>
  );
}

export const inputCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200";
