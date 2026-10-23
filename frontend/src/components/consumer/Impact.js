"use client";
import { Leaf, Cloud, PiggyBank, ShoppingBasket } from "lucide-react";
import { useStore } from "@/context/StoreContext";
import { co2Saved, money } from "@/lib/logic";
import { Card, KpiCard, PageHeader } from "../ui";

export default function Impact() {
  const { impact } = useStore();
  const co2 = co2Saved(impact.kgSaved);
  const trees = Math.round((co2 / 21) * 10) / 10; // ~21 kg CO2 absorbed per tree-year
  return (
    <>
      <PageHeader title="My Impact" subtitle="Every discounted item you rescue is food kept out of landfill." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard id="items-rescued" icon={ShoppingBasket} label="Items rescued" value={impact.itemsRescued} />
        <KpiCard id="food-saved" icon={Leaf} label="Food waste saved" value={`${impact.kgSaved} kg`} tone="amber" />
        <KpiCard id="co2-saved" icon={Cloud} label="CO₂e avoided" value={`${co2} kg`} tone="sky" />
        <KpiCard id="money-saved" icon={PiggyBank} label="Money saved" value={money(impact.moneySaved)} tone="violet" />
      </div>
      <Card title="What that means" className="mt-6">
        <p className="text-sm text-slate-600" data-testid="impact-blurb">Your rescued food avoided about <b>{co2} kg</b> of CO₂e — the yearly absorption of roughly <b>{trees}</b> trees.</p>
      </Card>
    </>
  );
}
