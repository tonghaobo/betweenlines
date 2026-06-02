import type { Metadata } from "next";
import "./globals.css";
import { I18nLayout } from "./I18nLayout";

export const metadata: Metadata = {
  title: "BetweenLines - Understand the vibe before you reply",
  description: "Understand the vibe before you reply. AI-powered relationship communication coaching.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
        <I18nLayout>
          <main className="mx-auto max-w-2xl px-4 py-8">
            {children}
          </main>
        </I18nLayout>
      </body>
    </html>
  );
}
