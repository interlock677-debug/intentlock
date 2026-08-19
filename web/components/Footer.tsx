'use client'

import { Shield, Github, Mail, FileText, BookOpen } from 'lucide-react'

const footerLinks = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'Security', href: '#evidence' },
    { label: 'Pricing', href: '#pricing' },
  ],
  Developers: [
    { label: 'Quickstart', href: '/docs/developer/QUICKSTART.md' },
    { label: 'Examples', href: '/docs/developer/EXAMPLES.md' },
    { label: 'SDK Reference', href: '/sdk/README.md' },
    { label: 'Architecture', href: '/docs/architecture/ARCHITECTURE.md' },
  ],
  Security: [
    { label: 'Security Report', href: '/docs/security/SECURITY_ASSURANCE_REPORT.md' },
    { label: 'Hardening Roadmap', href: '/docs/security/SECURITY_HARDENING_ROADMAP.md' },
    { label: 'Independent Audit', href: '/docs/security/FINAL_INDEPENDENT_AUDIT.md' },
  ],
  Business: [
    { label: 'Product Positioning', href: '/docs/business/PRODUCT_POSITIONING.md' },
    { label: 'Pricing', href: '/docs/business/PRICING.md' },
    { label: 'Enterprise Deployment', href: '/docs/commercial/ENTERPRISE_DEPLOYMENT.md' },
  ],
}

export function Footer() {
  return (
    <footer className="relative border-t border-white/5 py-16">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <a href="/" className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <Shield className="w-4 h-4 text-cyan-400" />
              </div>
              <span className="text-lg font-bold tracking-tight">IntentLock</span>
            </a>
            <p className="text-sm text-intent-muted">
              Security and authorization control plane for AI agents.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-sm font-semibold mb-4 tracking-widest uppercase text-intent-muted">
                {title}
              </h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      target={link.href.startsWith('http') ? '_blank' : undefined}
                      rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                      className="text-sm text-intent-muted hover:text-intent-text transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-white/5 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-intent-muted">
            © {new Date().getFullYear()} IntentLock. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="https://github.com/interlock677-debug/intentlock"
              target="_blank"
              rel="noopener noreferrer"
              className="text-intent-muted hover:text-intent-text transition-colors"
              aria-label="GitHub"
            >
              <Github className="w-5 h-5" />
            </a>
            <a
              href="mailto:interlock677@gmail.com"
              className="text-intent-muted hover:text-intent-text transition-colors"
              aria-label="Email"
            >
              <Mail className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
