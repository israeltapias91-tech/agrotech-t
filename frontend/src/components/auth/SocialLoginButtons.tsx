/* Área visual reservada para futura autenticación federada. Sin OAuth/OIDC. */
const providers = ['Google', 'Microsoft', 'Apple']

export default function SocialLoginButtons() {
  return (
    <div className="mt-6">
      <div className="mb-3 flex items-center gap-3 text-xs text-neutral-400">
        <span className="h-px flex-1 bg-neutral-200" />
        Continuar con
        <span className="h-px flex-1 bg-neutral-200" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        {providers.map((p) => (
          <button
            key={p}
            type="button"
            disabled
            title="Disponible próximamente"
            className="cursor-not-allowed rounded-lg border border-neutral-200 bg-neutral-50 px-2 py-2 text-sm font-medium text-neutral-400"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
