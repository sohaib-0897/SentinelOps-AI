import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {title: "SentinelOps AI · Incident Command", description: "Evidence-driven cloud incident investigation and controlled remediation."};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
