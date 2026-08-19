'use client'

import { motion } from 'framer-motion'
import { Check } from 'lucide-react'

const tiers = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'Open source, 1 agent, 100 intents/day, community support.',
    cta: 'Get Started',
    href: '/docs/developer/QUICKSTART.md',
    features: [
      '1 agent',
      '100 intents/day',
      '1 HITL approver',
      '10 policy rules',
      'Community support',
      'Local / Docker Compose',
    ],
  },
  {
    name: 'Pro',
    price: '$49',
    period: '/seat/mo',
    description: '10 agents, 10k intents/day, SSO, priority support.',
    cta: 'Upgrade to Pro',
    href: '/docs/business/PRICING.md',
    features: [
      '10 agents',
      '10,000 intents/day',
      '5 HITL approvers',
      '100 policy rules',
      'Priority support (24h)',
      'SSO (SAML 2.0 / OIDC)',
      'Single-region cloud, Docker, K8s',
    ],
    popular: true,
  },
  {
    name: 'Business',
    price: '$199',
    period: '/seat/mo',
    description: '100 agents, 100k intents/day, RBAC, SIEM adapter ports, compliance exports.',
    cta: 'Contact Sales',
    href: 'mailto:interlock677@gmail.com',
    features: [
      '100 agents',
      '100,000 intents/day',
      '25 HITL approvers',
      '1,000 policy rules',
      'Priority support (8h) + CSM',
      'Multi-region, K8s, Terraform',
      'Identity-based RBAC',
      'SIEM adapter ports',
      'Compliance exports',
    ],
  },
]

export function PricingSection() {
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
            Simple, <span className="gradient-text">transparent</span> pricing
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            Start free. Scale when you need to.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {tiers.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className={`relative rounded-2xl p-8 ${tier.popular ? 'glass-panel border-cyan-500/30' : 'glass-panel'}`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-xs font-medium text-cyan-300">
                  Most popular
                </div>
              )}
              
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-4xl font-bold">{tier.price}</span>
                  <span className="text-intent-muted">{tier.period}</span>
                </div>
                <p className="text-sm text-intent-muted mt-3">{tier.description}</p>
              </div>

              <ul className="space-y-3 mb-8">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-sm">
                    <Check className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
                    <span className="text-intent-muted">{feature}</span>
                  </li>
                ))}
              </ul>

              <a
                href={tier.href}
                target={tier.href.startsWith('http') ? '_blank' : undefined}
                rel={tier.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                className={`block w-full py-3 px-6 rounded-xl text-center font-medium transition-all duration-200 ${
                  tier.popular
                    ? 'bg-cyan-500 hover:bg-cyan-400 text-black'
                    : 'glass-panel hover:border-cyan-500/30 text-intent-text'
                }`}
              >
                {tier.cta}
              </a>
            </motion.div>
          ))}
        </div>

        <p className="text-center text-sm text-intent-muted mt-12">
          See{' '}
          <a href="/docs/business/PRICING.md" className="text-cyan-400 hover:underline">
            docs/business/PRICING.md
          </a>{' '}
          for full feature comparisons.
        </p>
      </div>
    </section>
  )
}
