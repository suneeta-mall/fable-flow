import { Label, TextInput, TextArea } from './ui'
import ImproveMenu from './ImproveMenu'

/**
 * Labeled input/textarea with an optional AI "Improve" menu in the header.
 * Pass `field` (and `actions`/`context`) to enable AI assist; omit to render a
 * plain field.
 */
export default function EditField({
  label,
  value,
  onChange,
  multiline = false,
  rows = 6,
  type = 'text',
  placeholder,
  field,
  context,
  actions,
  improveText,
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        {field && (
          <ImproveMenu
            field={field}
            text={improveText ?? value}
            context={context}
            actions={actions}
            onAccept={onChange}
          />
        )}
      </div>
      {multiline ? (
        <TextArea value={value} onChange={onChange} rows={rows} placeholder={placeholder} />
      ) : (
        <TextInput value={value} onChange={onChange} type={type} placeholder={placeholder} />
      )}
    </div>
  )
}
