import { Card, Label, TextInput } from './ui'
import EditField from './EditField'

function ListEditor({ label, items, onChange }) {
  const list = items || []
  const update = (i, v) => onChange(list.map((x, j) => (j === i ? v : x)))
  const add = () => onChange([...list, ''])
  const remove = (i) => onChange(list.filter((_, j) => j !== i))
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <button onClick={add} className="text-xs font-medium text-primary-700 hover:underline">
          + Add
        </button>
      </div>
      {list.map((item, i) => (
        <div key={i} className="flex gap-2">
          <TextInput value={item} onChange={(v) => update(i, v)} />
          <button onClick={() => remove(i)} className="text-xs text-red-600 hover:underline">
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}

export default function BiographyPanel({ biography, targetAge, actions, onChange }) {
  if (!biography) return null
  const bio = biography
  const ctx = { target_age: targetAge }
  const set = (key) => (value) => onChange({ [key]: value })

  return (
    <Card title="Featured personality biography">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <EditField label="Name" value={bio.name} onChange={set('name')} />
        <EditField label="Title" value={bio.title} onChange={set('title')} />
        <EditField label="Lifespan" value={bio.lifespan} onChange={set('lifespan')} />
        <EditField label="One-line" value={bio.one_line} onChange={set('one_line')} />
      </div>
      <EditField
        label="Summary"
        value={bio.summary}
        onChange={set('summary')}
        multiline
        rows={6}
        field="biography"
        actions={actions}
        context={ctx}
      />
      <ListEditor label="Fun facts" items={bio.fun_facts} onChange={set('fun_facts')} />
      <EditField
        label="Why inspiring"
        value={bio.why_inspiring}
        onChange={set('why_inspiring')}
        multiline
        rows={3}
      />
    </Card>
  )
}
