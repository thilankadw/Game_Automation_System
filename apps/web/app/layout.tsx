import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Game Automation System",
    template: "%s · Game Automation System",
  },
  description:
    "Operate games, providers, and ROI sets from a single automation control plane.",
};

/**
 * Root document that applies the JetBrains Mono font and application chrome.
 */
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html className={jetbrainsMono.variable} lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
