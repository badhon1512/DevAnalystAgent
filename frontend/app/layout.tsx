import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Self-hosted at build time, so there is no runtime request to Google and no
// flash of unstyled text.
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono-code",
});

export const metadata: Metadata = {
  title: "ProductAI",
  description: "Agentic analyst for product sales & inventory",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Left zoomable on purpose: locking zoom breaks the page for anyone who
  // needs to magnify it.
  maximumScale: 5,
  themeColor: "#020617",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        {children}
      </body>
    </html>
  );
}
