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
    "Inspect, commit, compare, and recover structured datasets with Chronos.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "Chronos - Structured Data Versioning",
    description: "Structured data, versioned with confidence.",
    type: "website",
    images: [{ url: "/og.png", width: 1792, height: 896, alt: "Chronos structured data versioning" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Chronos - Structured Data Versioning",
    description: "Structured data, versioned with confidence.",
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
