'use client'

import { motion } from 'framer-motion'
import { Brain, FileText, CheckCircle2, Users, BarChart3 } from 'lucide-react'

const problemSteps = [
  {
    icon: Brain,
    label: 'Intent',
    description: 'An AI agent proposes a tool action based on user request and reasoning.',
  },
  {
    icon: FileText,
    label: 'Policy',
    description: 'The proposed action is evaluated against versioned, testable policy rules.',
  },
  {
    icon: CheckCircle2,
    label: 'Authorization',
    description: 'IntentLock decides: allow, deny, or require human approval before execution.',
  },
  {
    icon: Users,
    label: 'Approval',
    description: 'High-risk actions enter a durable HITL queue with RBAC and audit trail.',
  },
  {
    icon: BarChart3,
    label: 'Audit',
    description: 'Every decision is recorded in a tamper-evident log with SHA-256 hash chains.',
  },
]

export function ProblemSection() {
  return (
    <section className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-950/10 to-transparent" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:50px_50px]" />
      
      <div className="relative max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            AI agents don't just generate text.{' '}
            <span className="gradient-text">They can take action.</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto leading-relaxed">
            Without a control plane between intent and execution, an agent can interact with APIs, databases, 
            files, infrastructure, and financial systems. The security question becomes: <span className="text-intent-text font-medium">should this action be allowed?</span>
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
          {problemSteps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="group relative p-6 rounded-2xl glass-panel hover:border-cyan-500/20 transition-all duration-300 text-center"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
              
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                  <step.icon className="w-6 h-6 text-cyan-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2 tracking-tight">{step.label}</h3>
                <p className="text-sm text-intent-muted leading-relaxed">{step.description}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-16 text-center"
        >
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full glass-panel">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-sm font-medium text-cyan-300">
              IntentLock is the control layer between AI agents and consequential actions.
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
