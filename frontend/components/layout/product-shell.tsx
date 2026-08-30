import type { ReactNode } from "react";


function AequorMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className="h-9 w-9">
      <path d="M24 4 42 14.5v19L24 44 6 33.5v-19L24 4Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="m14 30 10-17 10 17M18 25h12" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}


export function ProductShell({ children }: { children: ReactNode }) {
  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-6 sm:px-8 lg:px-12 lg:py-9">
      <header className="flex items-center justify-between border-b border-[var(--line)] pb-5">
        <div className="flex items-center gap-3 text-[var(--aqua)]">
          <AequorMark />
          <div>
            <p className="text-sm font-semibold tracking-[0.28em] text-[var(--ink)]">AEQUOR HEALTH</p>
            <p className="mt-0.5 text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">System foundation</p>
          </div>
        </div>
        <span className="rounded-full border border-[rgba(93,228,207,.22)] bg-[var(--aqua-soft)] px-3 py-1.5 text-[10px] font-semibold tracking-[0.18em] text-[var(--aqua)] sm:text-xs">
          PHASE 2
        </span>
      </header>
      {children}
      <footer className="mt-auto flex flex-col gap-2 border-t border-[var(--line)] pt-5 text-[11px] uppercase tracking-[0.14em] text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between">
        <span>Architecture prototype · Not a diagnostic system</span>
        <span>Local edge environment</span>
      </footer>
    </main>
  );
}
