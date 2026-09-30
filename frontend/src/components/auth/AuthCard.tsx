import type { ReactNode } from 'react'

export default function AuthCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="mb-6 lg:hidden">
        <p className="text-xl font-bold text-forest-900">AgroTech-T</p>
        <p className="text-xs text-neutral-500">Sistema inteligente de gestión agropecuaria</p>
      </div>
      <h1 className="text-2xl font-bold text-neutral-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-neutral-500">{subtitle}</p>}
      <div className="mt-6">{children}</div>
    </section>
  )
}
