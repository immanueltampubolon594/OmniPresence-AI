import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniPresence - Smart Workplace Analytics",
  description: "Enterprise Spatial Intelligence & Real-time Desk Occupancy System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-sans bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}