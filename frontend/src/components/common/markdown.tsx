import ReactMarkdown from 'react-markdown'

import { cn } from '@/lib/utils'

/** Renders agent-written Markdown. Raw HTML in the source is not rendered (react-markdown default). */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn('grid gap-2 text-body-md text-on-surface-variant', className)}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h3 className="mt-2 text-headline-lg font-semibold text-on-surface">{children}</h3>,
          h2: ({ children }) => <h3 className="mt-2 text-headline-sm font-semibold text-on-surface">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-2 text-headline-sm font-semibold text-on-surface">{children}</h4>,
          strong: ({ children }) => <strong className="font-semibold text-on-surface">{children}</strong>,
          ul: ({ children }) => <ul className="ml-5 list-disc space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="ml-5 list-decimal space-y-1">{children}</ol>,
          code: ({ children }) => <code className="rounded bg-surface-lowest px-1 py-0.5 font-mono text-code text-telemetry">{children}</code>,
          pre: ({ children }) => <pre className="overflow-x-auto rounded-md bg-surface-lowest p-3">{children}</pre>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer noopener" className="text-brand underline">
              {children}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
