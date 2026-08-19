'use client'

import { motion } from 'framer-motion'
import { Terminal, Github, FileText, Rocket } from 'lucide-react'

const developerLinks = [
  { label: 'Documentation', href: '/docs', icon: FileText },
  { label: 'Quickstart', href: '/docs/developer/QUICKSTART.md', icon: Rocket },
  { label: 'Examples', href: '/docs/developer/EXAMPLES.md', icon: Terminal },
  { label: 'GitHub', href: 'https://github.com/interlock677-debug/intentlock', icon: Github },
]

export function DeveloperSection() {
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
            Built for <span className="gradient-text">developers</span>
          </h2>
          <p className="text-lg text-intent-muted max-w-2xl mx-auto">
            Drop-in SDK, LangChain wrapper, and comprehensive documentation.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Code example */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative"
          >
            <div className="glass-panel rounded-2xl overflow-hidden">
              <div className="flex items-center gap-2 px-6 py-4 border-b border-white/5">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-4 text-xs text-intent-muted font-mono">example.py</span>
              </div>
              <pre className="p-6 text-sm leading-relaxed overflow-x-auto">
                <code className="text-intent-text">
                  <span className="text-cyan-400">from</span> sdk.intentlock <span className="text-cyan-400">import</span> IntentLockGuard, SecurityError{'\n'}
                  {'\n'}
                  client = IntentLockGuard( {'\n'}
                  {'  '}base_url=<span className="text-emerald-400">"http://localhost:8000/api/v1/intent/verify"</span>,{'\n'}
                  {'  '}execute_url=<span className="text-emerald-400">"http://localhost:8000/api/v1/intent/execute"</span>,{'\n'}
                  {'  '}auth_token=token,{'\n'}
                  ){'\n'}
                  {'\n'}
                  <span className="text-cyan-400">try</span>:{'\n'}
                  {'  '}execution_token = client.verify_intent( {'\n'}
                  {'    '}tool_name=<span className="text-emerald-400">"database_query"</span>,{'\n'}
                  {'    '}tool_arguments={{<span className="text-emerald-400">"query"</span>: <span className="text-emerald-400">"SELECT * FROM users LIMIT 10"</span>}},{'\n'}
                  {'    '}user_prompt=<span className="text-emerald-400">"List all active users"</span>,{'\n'}
                  {'    '}agent_id=<span className="text-emerald-400">"agent-001"</span>,{'\n'}
                  {'  '}){'\n'}
                  {'  '}result = client.consume_execution_token(execution_token){'\n'}
                  {'  '}print(<span className="text-emerald-400">"Action executed:"</span>, result){'\n'}
                  <span className="text-cyan-400">except</span> SecurityError <span className="text-cyan-400">as</span> exc:{'\n'}
                  {'  '}print(<span className="text-emerald-400">f"IntentLock denied execution: {exc}"</span>)
                </code>
              </pre>
            </div>
          </motion.div>

          {/* Installation and links */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="space-y-6"
          >
            <div className="glass-panel rounded-2xl p-8">
              <h3 className="text-xl font-semibold mb-4">Installation</h3>
              <div className="bg-black/40 rounded-lg p-4 font-mono text-sm text-cyan-300 border border-cyan-500/20">
                pip install intentlock
              </div>
            </div>

            <div className="glass-panel rounded-2xl p-8">
              <h3 className="text-xl font-semibold mb-4">Resources</h3>
              <div className="space-y-3">
                {developerLinks.map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 text-intent-muted hover:text-cyan-400 transition-colors group"
                  >
                    <link.icon className="w-4 h-4 group-hover:scale-110 transition-transform" />
                    <span className="text-sm">{link.label}</span>
                  </a>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
