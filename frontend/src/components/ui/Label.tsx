import type { LabelHTMLAttributes, ReactNode } from 'react'

type Props = LabelHTMLAttributes<HTMLLabelElement> & {
  children: ReactNode
}

export default function Label({ children, className = '', ...rest }: Props) {
  return (
    <label className={`mb-1 block text-sm font-medium text-neutral-700 ${className}`} {...rest}>
      {children}
    </label>
  )
}
