import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RideOps 城市出行助手",
  description: "面向共享出行用户的智能客服与安全协作助手",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
