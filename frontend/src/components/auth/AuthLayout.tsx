import type { ReactNode } from 'react'

/* Dos columnas en desktop (marca + formulario), una sola en móvil. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-sand-100 lg:flex-row">
      <aside className="relative hidden overflow-hidden bg-forest-950 lg:flex lg:w-1/2 lg:flex-col lg:justify-between lg:p-12">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, rgba(62,154,104,0.35), transparent 45%), radial-gradient(circle at 80% 70%, rgba(169,138,91,0.30), transparent 45%), repeating-linear-gradient(115deg, transparent 0 22px, rgba(255,255,255,0.04) 22px 23px)',
          }}
        />
        <div className="relative">
          <p className="text-2xl font-bold tracking-tight text-white">AgroTech-T</p>
          <p className="mt-1 text-sm text-forest-200">Sistema inteligente de gestión agropecuaria</p>
        </div>
        <div className="relative max-w-md">
          <div className="mb-4 flex items-center gap-2 text-forest-200" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <path d="M20 4C20 4 10 14 10 24a10 10 0 0 0 20 0C30 14 20 4 20 4Z" stroke="currentColor" strokeWidth="2" />
              <path d="M20 14v18M20 20l-5-3M20 20l5-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M6 32h28" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="3 4" />
            </svg>
          </div>
          <p className="text-xl font-medium leading-snug text-white">
            Cultivos, datos y decisiones conectadas en un solo sistema.
          </p>
          <p className="mt-2 text-sm text-forest-200">
            Monitoreo, trazabilidad y gestión pensados para el campo y la tecnología.
          </p>
        </div>
        <p className="relative text-xs text-forest-200/70">Agricultura + tecnología + confianza</p>
      </aside>
      <main className="flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">{children}</div>
      </main>
    </div>
  )
}
