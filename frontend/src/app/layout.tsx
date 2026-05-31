import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chat Coach - Understand the vibe before you reply",
  description: "Paste your chat and get instant insight.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
        <main className="mx-auto max-w-2xl px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
