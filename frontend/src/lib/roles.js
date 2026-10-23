import { Store, ShoppingBasket, Truck } from "lucide-react";

export const ROLES = [
  { id: "manager", label: "Store Manager", href: "/manager", icon: Store, blurb: "Inventory, markdowns and surplus routing" },
  { id: "consumer", label: "Shopper", href: "/consumer", icon: ShoppingBasket, blurb: "Grab discounted near-expiry food nearby" },
  { id: "partner", label: "B2B / NGO Partner", href: "/partner", icon: Truck, blurb: "Bid on or claim bulk surplus lots" },
];

