import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const noto = localFont({
  src: "./fonts/NotoSansThai.ttf",
  weight: "100 900",
  display: "swap",
  variable: "--font-noto",
});

export const metadata: Metadata = {
  title: "SplitBill: แบ่งบิลให้ลงตัว",
  description: "บันทึกค่าใช้จ่ายกับเพื่อน ดูส่วนแบ่งและยอดสุทธิได้ครบทุกสตางค์",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <body className={noto.variable}>{children}</body>
    </html>
  );
}
