import type { Metadata } from "next";
import { Playfair_Display, DM_Sans, JetBrains_Mono } from "next/font/google";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Shongkhep AI — Bangla & English Summarizer",
  description:
    "AI-powered article summarization for Bangla and English content. Built for Bangladesh.",
  keywords: ["bangla summarizer", "ai summarization", "bangladesh", "shongkhep"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn" className={`${playfair.variable} ${dmSans.variable} ${jetbrains.variable}`}>
      <body className="font-body bg-ink-950 text-ink-100 antialiased">
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1e1f28",
              color: "#e1e2e6",
              border: "1px solid #3e4050",
              fontFamily: "var(--font-body)",
            },
            success: { iconTheme: { primary: "#329666", secondary: "#0a2419" } },
            error:   { iconTheme: { primary: "#ef4444", secondary: "#1e1f28" } },
          }}
        />
        {children}
      </body>
    </html>
  );
}
