'use client'

import { Suspense, lazy } from 'react'

const Spline = lazy(() => import('@splinetool/react-spline'))

interface SplineSceneProps {
  scene: string
  className?: string
}

export function SplineScene({ scene, className }: SplineSceneProps) {
  if (!scene) {
    return <SecurityCoreFallback className={className} />
  }

  return (
    <Suspense
      fallback={
        <div className="w-full h-full flex items-center justify-center">
          <span className="loader"></span>
        </div>
      }
    >
      <Spline
        scene={scene}
        className={className}
      />
    </Suspense>
  )
}

function SecurityCoreFallback({ className }: { className?: string }) {
  return (
    <div className={`relative w-full h-full min-h-[500px] ${className || ''}`}>
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:50px_50px]" />
      
      {/* Radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,182,212,0.15)_0%,transparent_70%)]" />
      
      {/* Central core */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          {/* Outer ring */}
          <div className="absolute -inset-20 rounded-full border border-cyan-500/20 animate-[spin_20s_linear_infinite]" />
          <div className="absolute -inset-14 rounded-full border border-cyan-500/10 animate-[spin_15s_linear_infinite_reverse]" />
          
          {/* Core */}
          <div className="relative w-40 h-40 rounded-full bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/30 flex items-center justify-center backdrop-blur-sm animate-pulse-slow">
            <div className="text-center">
              <div className="text-2xl font-bold tracking-widest text-cyan-300">IL</div>
              <div className="text-[10px] tracking-[0.3em] text-cyan-500/80 uppercase mt-1">IntentLock</div>
            </div>
          </div>

          {/* Orbiting nodes */}
          {[
            { label: 'AGENT', angle: 0, delay: '0s' },
            { label: 'POLICY', angle: 72, delay: '0.5s' },
            { label: 'RISK', angle: 144, delay: '1s' },
            { label: 'AUDIT', angle: 216, delay: '1.5s' },
            { label: 'APPROVE', angle: 288, delay: '2s' },
          ].map((node, i) => {
            const rad = (node.angle * Math.PI) / 180
            const x = Math.cos(rad) * 120
            const y = Math.sin(rad) * 120
            return (
              <div
                key={node.label}
                className="absolute w-16 h-16 -ml-8 -mt-8 rounded-full glass-panel flex items-center justify-center"
                style={{
                  left: `calc(50% + ${x}px)`,
                  top: `calc(50% + ${y}px)`,
                  animationDelay: node.delay,
                }}
              >
                <span className="text-[10px] font-medium tracking-widest text-cyan-300/80 uppercase">
                  {node.label}
                </span>
              </div>
            )
          })}

          {/* Connection lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ width: '400px', height: '400px', marginLeft: '-200px', marginTop: '-200px' }}>
            {[0, 72, 144, 216, 288].map((angle, i) => {
              const rad = (angle * Math.PI) / 180
              const x = Math.cos(rad) * 120
              const y = Math.sin(rad) * 120
              return (
                <line
                  key={angle}
                  x1="200"
                  y1="200"
                  x2={200 + x}
                  y2={200 + y}
                  stroke="rgba(6, 182, 212, 0.2)"
                  strokeWidth="1"
                  className="animate-pulse-slow"
                  style={{ animationDelay: `${i * 0.3}s` }}
                />
              )
            })}
          </svg>
        </div>
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400/40 rounded-full animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 4}s`,
              animationDuration: `${3 + Math.random() * 3}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}
