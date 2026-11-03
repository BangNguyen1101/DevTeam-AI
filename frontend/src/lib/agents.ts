import { Brain, ClipboardList, Code2, DraftingCompass, LayoutTemplate, ShieldCheck, TestTubes, type LucideIcon } from 'lucide-react'

export interface AgentMeta {
  abbr: string
  icon: LucideIcon
  /** Tailwind classes for the agent's identity chip */
  tone: string
  /** Bar colour used in charts */
  color: string
}

const META: Record<string, AgentMeta> = {
  manager: { abbr: 'MG', icon: Brain, tone: 'bg-brand-strong/20 text-brand', color: '#adc6ff' },
  business_analyst: { abbr: 'BA', icon: ClipboardList, tone: 'bg-agent/15 text-agent', color: '#c0c1ff' },
  architect: { abbr: 'AR', icon: DraftingCompass, tone: 'bg-telemetry/15 text-telemetry', color: '#4cd7f6' },
  backend_dev: { abbr: 'BE', icon: Code2, tone: 'bg-brand/15 text-brand', color: '#4d8eff' },
  frontend_dev: { abbr: 'FE', icon: LayoutTemplate, tone: 'bg-processing/15 text-processing', color: '#818cf8' },
  qa_tester: { abbr: 'QA', icon: TestTubes, tone: 'bg-success/15 text-success', color: '#10b981' },
  code_reviewer: { abbr: 'CR', icon: ShieldCheck, tone: 'bg-warning/15 text-warning', color: '#f59e0b' },
}

const FALLBACK: AgentMeta = { abbr: '??', icon: Brain, tone: 'bg-surface-high text-on-surface-variant', color: '#8c909f' }

export const agentMeta = (code: string | null | undefined): AgentMeta => (code && META[code]) || FALLBACK

export const AGENT_ORDER = Object.keys(META)
