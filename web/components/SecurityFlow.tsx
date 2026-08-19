'use client'

import { motion } from 'framer-motion'
import { Shield, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'

const flowSteps = [
  { label: 'AI AGENT', icon: Shield, color: 'text-slate-400' },
  { label: 'INTENT', icon: ShieldCheck, color: 'text-cyan-400' },
  { label: 'INTENTLOCK', icon: Shield, color: 'text-cyan-300' },
  { label: 'POLICY', icon: ShieldCheck, color: 'text-cyan-400' },
  { label: 'RISK', icon: ShieldAlert, color: 'text-amber-400' },
  { label: 'HUMAN APPROVAL', icon: ShieldCheck, color: 'text-cyan-400' },
  { label: 'AUDIT TRAIL', icon: ShieldX, color: 'text-emerald-400' },
]

export function SecurityFlow() {
  return (
    <section className="relative py-32 overflow-hidden">
      {/* Background */}
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
            Every action evaluated.{' '}
            <span className="gradient-text">Every decision recorded.</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            IntentLock sits between your AI agents and the tools they call, enforcing policy at the exact moment of intent.
          </p>
        </motion.div>

        {/* Flow visualization */}
        <div className="relative">
          {/* Desktop flow */}
          <div className="hidden lg:flex items-center justify-between">
            {flowSteps.map((step, i) => (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="flex flex-col items-center"
              >
                <div className="relative">
                  <div className="w-20 h-20 rounded-2xl glass-panel flex items-center justify-center mb-4 relative overflow-hidden group hover:border-cyan-500/30 transition-colors duration-300">
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <step.icon className={`w-8 h-8 ${step.color}`} />
                  </div>
                  {i < flowSteps.length - 1 && (
                    <div className="absolute top-10 left-20 w-16 h-px bg-gradient-to-r from-cyan-500/40 to-transparent" />
                  )}
                </div>
                <span className="text-xs font-medium tracking-widest text-intent-muted uppercase">
                  {step.label}
                </span>
              </motion.div>
            ))}
          </div>

          {/* Mobile flow */}
          <div className="lg:hidden flex flex-col items-center space-y-4">
            {flowSteps.map((step, i) => (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="flex items-center w-full max-w-sm"
              >
                <div className="w-14 h-14 rounded-xl glass-panel flex items-center justify-center mr-4 flex-shrink-0">
                  <step.icon className={`w-6 h-6 ${step.color}`} />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold tracking-wide">{step.label}</div>
                  {i < flowSteps.length - 1 && (
                    <div className="mt-2 h-8 w-px bg-gradient-to-b from-cyan-500/40 to-transparent ml-7" />
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
