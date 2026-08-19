'use client'

import { motion } from 'framer-motion'
import { ChevronDown, Shield, ArrowRight, Play } from 'lucide-react'
import { SplineScene } from '@/components/SplineScene'
import { ProblemSection } from '@/components/ProblemSection'
import { SecurityFlow } from '@/components/SecurityFlow'
import { FeaturesSection } from '@/components/FeaturesSection'
import { UseCasesSection } from '@/components/UseCasesSection'
import { DemoSection } from '@/components/DemoSection'
import { EvidenceSection } from '@/components/EvidenceSection'
import { DeveloperSection } from '@/components/DeveloperSection'
import { PricingSection } from '@/components/PricingSection'
import { CTASection } from '@/components/CTASection'
import { Navbar } from '@/components/Navbar'
import { Footer } from '@/components/Footer'

const splineSceneUrl = process.env.NEXT_PUBLIC_SPLINE_SCENE_URL || ''

export default function Home() {
  return (
    <div className="min-h-screen" id="main-content">
      <Navbar />

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        {/* Background layers */}
        <div className="absolute inset-0 bg-gradient-to-b from-cyan-950/20 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(6,182,212,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:50px_50px]" />
        
        {/* Floating orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-cyan-400/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }} />

        <div className="relative max-w-7xl mx-auto px-6 py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Text content */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="text-center lg:text-left"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel mb-8"
              >
                <Shield className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-medium tracking-widest uppercase text-cyan-300">
                  Proof-of-Intent Authorization
                </span>
              </motion.div>

              <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-[1.1]">
                Your AI agents can act.
                <br />
                <span className="gradient-text">IntentLock</span> makes sure they act safely.
              </h1>

              <p className="text-lg md:text-xl text-intent-muted mb-10 max-w-xl mx-auto lg:mx-0 leading-relaxed">
                Authorize every tool call. Enforce policy. Require approval for high-risk actions. Keep an auditable record.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 mb-8">
                <a
                  href="/docs/developer/QUICKSTART.md"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-semibold transition-all duration-200 hover:scale-105 w-full sm:w-auto justify-center"
                >
                  Protect an Agent
                  <ArrowRight className="w-4 h-4" />
                </a>
                <a
                  href="https://github.com/interlock677-debug/intentlock"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl glass-panel hover:border-cyan-500/30 font-medium transition-all duration-200 w-full sm:w-auto justify-center"
                >
                  <Play className="w-4 h-4" />
                  View on GitHub
                </a>
              </div>

              <div className="flex items-center justify-center lg:justify-start gap-6 text-xs text-intent-muted">
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  760 tests passing
                </span>
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  99.92% coverage
                </span>
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  Open source
                </span>
              </div>
            </motion.div>

            {/* Right: 3D Visual */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.4 }}
              className="relative h-[500px] lg:h-[600px]"
            >
              <div className="absolute inset-0 rounded-3xl overflow-hidden glass-panel">
                <SplineScene
                  scene={splineSceneUrl}
                  className="w-full h-full"
                />
              </div>
            </motion.div>
          </div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-xs text-intent-muted tracking-widest uppercase">Scroll</span>
          <ChevronDown className="w-4 h-4 text-intent-muted animate-bounce" />
        </motion.div>
      </section>

      {/* Problem Section */}
      <ProblemSection />

      {/* Security Flow */}
      <SecurityFlow />

      {/* Features */}
      <FeaturesSection />

      {/* Use Cases */}
      <UseCasesSection />

      {/* Demo */}
      <DemoSection />

      {/* Evidence */}
      <EvidenceSection />

      {/* Developer */}
      <DeveloperSection />

      {/* Pricing */}
      <PricingSection />

      {/* CTA */}
      <CTASection />

      {/* Footer */}
      <Footer />
    </div>
  )
}
