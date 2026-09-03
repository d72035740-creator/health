import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "Aequor Health | Personalized Surveillance Prototype",
  description: "Patient and clinician product views for the Aequor Health simulation prototype.",
};


export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
