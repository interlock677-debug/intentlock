'use client'

import { motion } from 'framer-motion'
import { Lock, ShieldCheck, FileText, Users, Activity, Settings } from 'lucide-react'

const features = [
  {
    icon: Lock,
    title: 'Agent Authorization',
    description: 'Control which agents can perform which actions with fine-grained identity-based policies.',
  },
  {
    icon: ShieldCheck,
    title: 'Tool Security',
    description: 'Validate tool calls and arguments before execution using regex, SQL parsing, and policy-as-code.',
  },
  {
    icon: FileText,
    title: 'Policy Enforcement',
    description: 'Centralize authorization and security policies with YAML-configured, versioned rules and rollback.',
  },
  {
    icon: Users,
    title: 'Human Approval',
    description: 'Require approval for high-risk operations with a durable, database-backed HITL queue and RBAC.',
  },
  {
    icon: Activity,
    title: 'Auditability',
    description: 'Maintain tamper-evident evidence of security decisions and actions with SHA-256 hash chains.',
  },
  {
    icon: Settings,
    title: 'Multi-Tenant Controls',
    description: 'Separate authorization and security boundaries between tenants with identity-based isolation.',
  },
]

export function FeaturesSection() {
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
            Built for the reality of{' '}
            <span className="gradient-text">agentic systems</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            Every capability you need to secure AI agents at the authorization layer.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="group relative p-8 rounded-2xl glass-panel hover:border-cyan-500/20 transition-all duration-300"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                  <feature.icon className="w-6 h-6 text-cyan-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3 tracking-tight">{feature.title}</h3>
                <p className="text-intent-muted leading-relaxed">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
