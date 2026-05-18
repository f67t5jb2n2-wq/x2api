import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "x2ding RSS Service",
  description: "API key based X/Twitter subscription RSS service.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
