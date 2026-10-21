import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Game Automation System",
  description: "Web dashboard for the Game Automation System",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
