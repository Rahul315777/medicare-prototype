import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";
// 1. Yahan Providers import kiya
import Providers from "@/components/providers"; 

// 👉 1. NAYA IMPORT: Voice Assistant ko yahan bulaya 👈
import VoiceAssistant from "@/components/VoiceAssistant";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Professional Metadata setup
export const metadata: Metadata = {
  title: "MediCare AI - Intelligent Healthcare",
  description: "Next-generation healthcare platform powered by AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/* Yahan body me bhi suppressHydrationWarning laga diya ji: */}
      <body 
        className="min-h-full flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50 transition-colors duration-300"
        suppressHydrationWarning
      >
        
        {/* 2. Yahan Providers se app ko lapet diya (wrap kar diya) */}
        <Providers>
          {children}
        </Providers>
        
        {/* 👉 2. NAYA BOT: Aapka floating voice assistant yahan laga diya 👈 */}
        <VoiceAssistant />

        {/* Pop-up notifications (success/error) ke liye */}
        <Toaster position="top-center" richColors />
      </body>
    </html>
  );
}