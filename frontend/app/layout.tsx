import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Andrea's · AI Beauty Try-On",
  description: "Explore hairstyle, makeup, and nail looks in Andrea's AI studio.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
