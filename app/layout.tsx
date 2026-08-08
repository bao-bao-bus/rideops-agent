import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RideOps Agent",
  description: "Shared mobility support agent workbench",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
