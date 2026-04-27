import { Geist_Mono, Instrument_Serif, Inter } from "next/font/google"
import Script from "next/script"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { cn } from "@/lib/utils"

const fontMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" })
const fontSansUi = Inter({ subsets: ["latin"], variable: "--font-sans-ui" })
const fontSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-serif",
})

const accentBootScript = `(function(){try{var m={blue:'#2563eb',slate:'#475569',teal:'#0f766e',stone:'#44403c'};var v=localStorage.getItem('lc-accent');document.documentElement.style.setProperty('--accent-boot',m[v]||m.blue);}catch(e){}})();`

const fontBootScript = `(function(){try{var mono='var(--font-mono),ui-monospace,\\"Cascadia Code\\",\\"Consolas\\",monospace';var sans='var(--font-sans-ui),ui-sans-serif,system-ui,sans-serif';var sys='ui-sans-serif,system-ui,-apple-system,\\"Segoe UI\\",Roboto,\\"Helvetica Neue\\",Arial,sans-serif';var serif='var(--font-serif),ui-serif,Georgia,serif';var m={mono:mono,sans:sans,system:sys,serif:serif};var v=localStorage.getItem('lc-font');document.documentElement.style.setProperty('--lc-body-font',m[v]||m.mono);}catch(e){}})();`

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "antialiased",
        fontMono.variable,
        fontSansUi.variable,
        fontSerif.variable,
        "font-mono"
      )}
    >
      <head>
        <Script
          id="accent-boot"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: accentBootScript }}
        />
        <Script
          id="font-boot"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: fontBootScript }}
        />
      </head>
      <body data-app="local-chat" suppressHydrationWarning>
        <ThemeProvider defaultTheme="system" enableSystem>
          {children}
          <Toaster position="top-right" richColors closeButton />
        </ThemeProvider>
      </body>
    </html>
  )
}
