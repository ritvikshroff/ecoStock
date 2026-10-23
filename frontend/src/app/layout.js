import "./globals.css";
import { StoreProvider } from "@/context/StoreContext";

export const metadata = { title: "ecoStock — Zero-Waste Inventory", description: "Zero-waste supermarket inventory and markdown platform" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="font-sans text-slate-800 antialiased">
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
