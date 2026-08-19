'use client'

import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, AlertTriangle, Code, Bug, Shield, FileSearch, Package } from 'lucide-react'

const evidenceItems = [
  { label: 'Automated tests', value: '760 passed, 5 skipped, 0 failed', icon: CheckCircle2, positive: true },
  { label: 'Statement coverage', value: '99.92%', icon: CheckCircle2, positive: true },
  { label: 'Branch coverage', value: '99.59%', icon: CheckCircle2, positive: true },
  { label: 'Static analysis (Ruff)', value: '0 errors', icon: CheckCircle2, positive: true },
  { label: 'Type checking (MyPy)', value: '0 issues', icon: CheckCircle2, positive: true },
  { label: 'Security scanner (Bandit)', value: '0 High/Medium issues', icon: CheckCircle2, positive: true },
  { label: 'Dependency audit (pip-audit)', value: '0 known vulnerabilities', icon: CheckCircle2, positive: true },
  { label: 'Adversarial tests', value: '88 passed', icon: Bug, positive: true },
  { label: 'SBOM', value: 'Generated (156 components)', icon: Package, positive: true },
]

const whatItShows = [
  'Automated security testing — adversarial tests cover JWT forgery, replay attacks, SQL injection, SSRF, path traversal, and prompt injection',
  'Dependency auditing — pip-audit runs in CI; SBOM is generated for supply-chain transparency',
  'Static analysis — Ruff, MyPy, Bandit, and Semgrep are configured in CI',
  'Threat model — documented in architecture and security assurance reports',
  'Security documentation — assurance report, hardening roadmap, and independent audit are in docs/security/',
]

const whatIsNotClaimed = [
  'This is not independent penetration testing by a qualified security firm',
  'This is not a SOC 2, HIPAA, PCI-DSS, or any regulatory compliance certification',
  'This is not a guarantee of security outcomes',
  'Testing evidence does not equal certification',
]

export function EvidenceSection() {
  return (
    <section className="relative py-32">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-950/50 to-transparent" />
      
      <div className="relative max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Current engineering <span className="gradient-text">verification</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            Automated repository and testing evidence from the IntentLock V4 codebase.
          </p>
        </motion.div>

        {/* Evidence grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
          {evidenceItems.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="glass-panel rounded-xl p-5 flex items-center gap-4"
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${item.positive ? 'bg-emerald-500/10' : 'bg-amber-500/10'}`}>
                <item.icon className={`w-5 h-5 ${item.positive ? 'text-emerald-400' : 'text-amber-400'}`} />
              </div>
              <div>
                <div className="text-sm font-medium text-intent-text">{item.label}</div>
                <div className="text-xs text-intent-muted font-mono mt-0.5">{item.value}</div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* What it shows */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto mb-12"
        >
          <div className="glass-panel rounded-2xl p-8">
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-cyan-400" />
              What the evidence shows
            </h3>
            <ul className="space-y-3">
              {whatItShows.map((item) => (
                <li key={item} className="flex items-start gap-3 text-intent-muted">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </motion.div>

        {/* What is not claimed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto"
        >
          <div className="glass-panel rounded-2xl p-8 border-red-500/10">
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              What is not claimed
            </h3>
            <ul className="space-y-3">
              {whatIsNotClaimed.map((item) => (
                <li key={item} className="flex items-start gap-3 text-intent-muted">
                  <XCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
