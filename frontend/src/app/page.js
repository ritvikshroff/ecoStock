import Link from "next/link";
import { Leaf, ArrowRight } from "lucide-react";
import { ROLES } from "@/lib/roles";

export default function Landing() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-emerald-50 to-white p-6">
      <Leaf className="text-emerald-600" size={44} />
      <h1 className="mt-3 text-4xl font-extrabold tracking-tight text-emerald-950" data-testid="landing-title">ecoStock</h1>
      <p className="mt-2 max-w-md text-center text-slate-600">Zero-waste inventory, smart markdowns and surplus routing for supermarkets. Choose your portal.</p>
      <div className="mt-10 grid w-full max-w-4xl gap-4 sm:grid-cols-3">
        {ROLES.map(({ id, label, href, icon: Icon, blurb }) => (
          <Link key={id} href={href} data-testid={`enter-${id}`} className="group rounded-2xl border border-emerald-100 bg-white p-6 shadow-sm transition hover:border-emerald-400 hover:shadow-md">
            <span className="inline-flex rounded-xl bg-emerald-100 p-3 text-emerald-700"><Icon size={24} /></span>
            <h2 className="mt-4 font-semibold text-slate-900">{label}</h2>
            <p className="mt-1 text-sm text-slate-500">{blurb}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-emerald-700">Enter portal <ArrowRight size={14} className="transition group-hover:translate-x-1" /></span>
          </Link>
        ))}
      </div>
    </main>
  );
}
