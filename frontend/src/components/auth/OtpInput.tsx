import { useRef } from 'react'

type Props = {
  length?: number
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

/* 6 casillas con avance automático, retroceso y pegado. Solo visual. */
export default function OtpInput({ length = 6, value, onChange, disabled }: Props) {
  const refs = useRef<Array<HTMLInputElement | null>>([])

  const set = (digits: string[]) => onChange(digits.join('').slice(0, length))

  const digits = value.padEnd(length, ' ').split('').slice(0, length)

  const handleChange = (i: number, v: string) => {
    const d = v.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[i] = d || ' '
    set(next)
    if (d && i < length - 1) refs.current[i + 1]?.focus()
  }

  const handleKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && digits[i] === ' ') refs.current[i - 1]?.focus()
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
    if (pasted) {
      onChange(pasted)
      refs.current[Math.min(pasted.length, length - 1)]?.focus()
    }
  }

  return (
    <div className="flex justify-between gap-2" role="group" aria-label="Código de 6 dígitos">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el
          }}
          value={d === ' ' ? '' : d}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          disabled={disabled}
          inputMode="numeric"
          autoComplete="one-time-code"
          aria-label={`Dígito ${i + 1}`}
          maxLength={1}
          className="h-12 w-11 rounded-lg border border-neutral-300 text-center text-xl font-bold text-neutral-900 focus:border-forest-600 sm:h-13 sm:w-12"
        />
      ))}
    </div>
  )
}
