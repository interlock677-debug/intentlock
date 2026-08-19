import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'IntentLock — Security Control Plane for AI Agents',
  description: 'Authorize, validate, monitor, and audit high-risk AI agent actions before they reach production systems.',
  openGraph: {
    title: 'IntentLock — Security Control Plane for AI Agents',
    description: 'Authorize, validate, monitor, and audit high-risk AI agent actions before they reach production systems.',
    type: 'website',
  },
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-intent-bg text-intent-text antialiased">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-cyan-500 focus:text-black">
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  )
}
