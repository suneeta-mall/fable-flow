import clsx from 'clsx'

export function Card({ title, children, className }) {
  return (
    <section className={clsx('rounded-xl border border-gray-200 bg-white shadow-sm', className)}>
      {title && (
        <header className="border-b border-gray-100 px-5 py-3 text-sm font-semibold text-gray-700">
          {title}
        </header>
      )}
      <div className="p-5 space-y-4">{children}</div>
    </section>
  )
}

export function Label({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-medium uppercase tracking-wide text-gray-500">
      {children}
    </label>
  )
}

export function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value ?? ''}
      placeholder={placeholder}
      onChange={(e) => onChange(type === 'number' ? toNumber(e.target.value) : e.target.value)}
      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
    />
  )
}

export function TextArea({ value, onChange, rows = 6, placeholder, mono }) {
  return (
    <textarea
      value={value ?? ''}
      rows={rows}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className={clsx(
        'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-relaxed focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500',
        mono && 'font-mono whitespace-pre',
      )}
    />
  )
}

export function Button({ children, onClick, variant = 'primary', disabled, type = 'button' }) {
  const styles = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700',
    ghost: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
    danger: 'bg-red-50 text-red-700 border border-red-200 hover:bg-red-100',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
        styles[variant],
      )}
    >
      {children}
    </button>
  )
}

function toNumber(v) {
  if (v === '') return null
  const n = Number(v)
  return Number.isNaN(n) ? v : n
}
