import type { ButtonHTMLAttributes } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean
}

export default function Button({ loading, children, className = '', disabled, ...rest }: Props) {
  return (
    <button
      type="submit"
      disabled={disabled || loading}
      className={`flex w-full items-center justify-center gap-2 rounded-lg bg-forest-700 px-4 py-2.5 font-semibold text-white transition hover:bg-forest-600 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...rest}
    >
      {loading ? 'Procesando…' : children}
    </button>
  )
}
