'use client'

import { motion } from 'framer-motion'
import { ShieldCheck, ShieldAlert, ShieldX, Shield } from 'lucide-react'

const demoSteps = [
  {
    label: 'Agent Request',
    value: 'Transfer $50,000',
    status: 'received',
    icon: Shield,
    color: 'text-slate-400',
  },
  {
    label: 'IntentLock',
    value: 'Evaluating...',
    status: 'evaluating',
    icon: ShieldCheck,
    color: 'text-cyan-400',
  },
  {
    label: 'Risk Assessment',
    value: 'HIGH RISK',
    status: 'risk',
    icon: ShieldAlert,
    color: 'text-amber-400',
  },
  {
    label: 'Policy Check',
    value: 'Exceeds user limit',
    status: 'policy',
    icon: ShieldX,
    color: 'text-red-400',
  },
  {
    label: 'Decision',
    value: 'Human Approval Required',
    status: 'decision',
    icon: Shield,
    color: 'text-cyan-300',
  },
  {
    label: 'Outcome',
    value: 'DENIED',
    status: 'outcome',
    icon: ShieldX,
    color: 'text-red-400',
  },
]

export function DemoSection() {
  return (
    <section className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-950/10 to-transparent" />
      
      <div className="relative max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            See the <span className="gradient-text">decision process</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            A demonstration of how IntentLock evaluates a high-risk tool action before execution.
          </p>
        </motion.div>

        <div className="max-w-4xl mx-auto">
          <div className="glass-panel rounded-2xl p-8 md:p-12 relative overflow-hidden">
            {/* Background glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
            
            <div className="relative space-y-0">
              {demoSteps.map((step, i) => (
                <motion.div
                  key={step.label}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.15 }}
                  className="flex items-start gap-6"
                >
                  {/* Timeline */}
                  <div className="flex flex-col items-center">
                    <div className={`w-12 h-12 rounded-xl glass-panel flex items-center justify-center flex-shrink-0 ${step.status === 'outcome' ? 'bg-red-500/10 border-red-500/20' : ''}`}>
                      <step.icon className={`w-5 h-5 ${step.color}`} />
                    </div>
                    {i < demoSteps.length - 1 && (
                      <div className="w-px h-12 bg-gradient-to-b from-cyan-500/30 to-transparent mt-2" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 pb-8">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-sm font-medium tracking-widest text-intent-muted uppercase">
                        {step.label}
                      </span>
                      {step.status === 'outcome' && (
                        <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
                          BLOCKED
                        </span>
                      )}
                    </div>
                    <p className="text-base font-mono text-intent-text/90">{step.value}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="mt-8 pt-8 border-t border-white/5 text-center">
              <p className="text-xs text-intent-muted">
                This is a demonstration. IntentLock does not execute financial transfers.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
