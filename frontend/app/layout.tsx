import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Incremental Multi-Agent Path Repair",
  description: "Dynamic warehouse simulation with incremental, negotiated plan repair",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen" suppressHydrationWarning>
        <header className="sticky top-0 z-20 border-b border-ink-700 bg-ink-950/90 backdrop-blur">
          <div className="mx-auto flex max-w-[1800px] items-center gap-6 px-4 py-2.5">
            <Link href="/" className="text-sm font-semibold text-accent">
              ⬡ Path Repair Lab
            </Link>
            <nav className="flex gap-4 text-sm text-slate-300">
              <Link href="/simulation" className="hover:text-white">Simulation</Link>
              <Link href="/experiments" className="hover:text-white">Experiments</Link>
            </nav>
            <span className="ml-auto hidden text-xs text-slate-500 md:block">
              Incremental Multi-Agent Path Repair for Dynamic Automated Warehouses
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-[1800px] px-4 py-4">{children}</main>
      </body>
    </html>
  );
}
