import { Geist_Mono } from "next/font/google"
import Script from "next/script"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { cn } from "@/lib/utils"

const fontMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" })

const accentBootScript = `(function(){try{var m={blue:'#2563eb',violet:'#7c3aed',emerald:'#10b981',rose:'#e11d48'};var v=localStorage.getItem('lc-accent');document.documentElement.style.setProperty('--accent-boot',m[v]||m.blue);}catch(e){}})();`

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn("antialiased", fontMono.variable, "font-mono")}
    >
      <head>
        <Script
          id="accent-boot"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: accentBootScript }}
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
