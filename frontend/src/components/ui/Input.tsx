import type { InputHTMLAttributes } from 'react'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean
}

export default function Input({ invalid, className = '', ...rest }: Props) {
  return (
    <input
      className={`w-full rounded-lg border bg-white px-3 py-2.5 text-[16px] text-neutral-900 placeholder:text-neutral-400 ${
        invalid ? 'border-red-500' : 'border-neutral-300 focus:border-forest-600'
      } ${className}`}
      {...rest}
    />
  )
}
