'use client'

import { motion } from 'framer-motion'
import { Database, DollarSign, Terminal, FileSearch, Building2, ServerOff } from 'lucide-react'

const useCases = [
  {
    icon: Database,
    title: 'Database Query Guard',
    description: 'Prevent destructive SQL and data exfiltration from agent-driven queries before they reach production data.',
    tier: 'Free',
  },
  {
    icon: DollarSign,
    title: 'Financial Transfer Approval',
    description: 'Require human approval for wire transfers, payroll changes, or invoice payments exceeding defined limits.',
    tier: 'Business',
  },
  {
    icon: Terminal,
    title: 'Shell Command Sandbox',
    description: 'Restrict agent shell access to approved commands and directories with policy-as-code rules.',
    tier: 'Pro',
  },
  {
    icon: FileSearch,
    title: 'Compliance Evidence Pack',
    description: 'Export HMAC-signed audit evidence for SOC 2, HIPAA, or internal review with tamper-evident logs.',
    tier: 'Business',
  },
  {
    icon: Building2,
    title: 'Multi-Tenant SaaS',
    description: 'Isolate tenants with hierarchical RBAC and per-tenant policy rules in a shared deployment.',
    tier: 'Enterprise',
  },
  {
    icon: ServerOff,
    title: 'Air-Gapped Deployment',
    description: 'Run IntentLock in a classified or disconnected environment with HSM-backed key management.',
    tier: 'Enterprise',
  },
]

export function UseCasesSection() {
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
            Built for <span className="gradient-text">real agent deployments</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            From local development to air-gapped enterprise, IntentLock secures the tool actions that matter.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {useCases.map((useCase, i) => (
            <motion.div
              key={useCase.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="group relative p-8 rounded-2xl glass-panel hover:border-cyan-500/20 transition-all duration-300"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              
              <div className="relative">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <useCase.icon className="w-5 h-5 text-cyan-400" />
                  </div>
                  <span className="text-xs font-medium tracking-widest text-intent-muted uppercase">
                    {useCase.tier}
                  </span>
                </div>
                <h3 className="text-xl font-semibold mb-3 tracking-tight">{useCase.title}</h3>
                <p className="text-intent-muted leading-relaxed text-sm">{useCase.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
