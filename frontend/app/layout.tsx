import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: "Chronos - Structured Data Versioning",
  description:
    "Content-addressed metrics for versioned structured data.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "Chronos - Structured Data Versioning",
    description: "Content-addressed metrics for versioned data.",
    type: "website",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "Chronos content-addressed versioning metrics" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Chronos - Structured Data Versioning",
    description: "Content-addressed metrics for versioned data.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
