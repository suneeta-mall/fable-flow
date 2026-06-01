import { Card, Label, TextInput } from './ui'
import EditField from './EditField'
import ImproveMenu from './ImproveMenu'

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

export default function ExperimentPanel({ experiment, targetAge, actions, onChange }) {
  if (!experiment) return null
  const ex = experiment
  const ctx = { target_age: targetAge }
  const set = (key) => (value) => onChange({ [key]: value })

  return (
    <Card title="Experiment / hands-on activity">
      <EditField label="Title" value={ex.title} onChange={set('title')} />
      <EditField label="Concept" value={ex.concept} onChange={set('concept')} multiline rows={2} />
      <ListEditor label="Materials" items={ex.materials} onChange={set('materials')} />
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Steps</Label>
          <ImproveMenu
            field="experiment"
            text={(ex.steps || []).join('\n')}
            context={ctx}
            actions={actions}
            onAccept={(result) => set('steps')(Array.isArray(result) ? result : [result])}
          />
        </div>
        <ListEditor label="" items={ex.steps} onChange={set('steps')} />
      </div>
      <EditField
        label="What to observe"
        value={ex.what_to_observe}
        onChange={set('what_to_observe')}
        multiline
        rows={2}
      />
      <EditField label="Safety note" value={ex.safety_note} onChange={set('safety_note')} />
    </Card>
  )
}
