export default function Spinner({ label = 'Cargando…' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-label={label}>
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-forest-200 border-t-forest-700" />
      <span className="text-sm text-neutral-600">{label}</span>
    </span>
  )
}
