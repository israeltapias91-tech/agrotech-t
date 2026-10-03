import type { InputHTMLAttributes } from 'react'
import Input from '../ui/Input'
import Label from '../ui/Label'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  error?: string
}

export default function AuthInput({ label, error, id, ...rest }: Props) {
  const fieldId = id ?? rest.name
  return (
    <div className="mb-4">
      <Label htmlFor={fieldId}>{label}</Label>
      <Input id={fieldId} invalid={Boolean(error)} aria-invalid={Boolean(error)} aria-describedby={error ? `${fieldId}-error` : undefined} {...rest} />
      {error && (
        <p id={`${fieldId}-error`} role="alert" className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
