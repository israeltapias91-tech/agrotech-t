import { useState } from 'react'
import AuthInput from './AuthInput'

type Props = Omit<React.ComponentProps<typeof AuthInput>, 'type'>

export default function PasswordInput(props: Props) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <AuthInput type={visible ? 'text' : 'password'} autoComplete="current-password" {...props} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        className="absolute right-3 top-9 text-sm font-medium text-forest-700 hover:text-forest-600"
      >
        {visible ? 'Ocultar' : 'Mostrar'}
      </button>
    </div>
  )
}
