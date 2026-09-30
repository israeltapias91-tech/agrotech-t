type Props = {
  kind: 'error' | 'success' | 'info'
  title?: string
  children: React.ReactNode
}

const styles: Record<Props['kind'], string> = {
  error: 'border-red-300 bg-red-50 text-red-800',
  success: 'border-forest-200 bg-forest-50 text-forest-900',
  info: 'border-sand-500/40 bg-sand-100 text-sand-900',
}

export default function Alert({ kind, title, children }: Props) {
  return (
    <div role="alert" className={`rounded-lg border px-3 py-2.5 text-sm ${styles[kind]}`}>
      {title && <p className="font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  )
}
