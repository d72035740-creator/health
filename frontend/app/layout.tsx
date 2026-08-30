import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "Aequor Health | Simulation Prototype",
  description: "Phase 0 system foundation for Aequor Health.",
};


export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

