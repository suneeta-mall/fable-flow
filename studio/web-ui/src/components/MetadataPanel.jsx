import { Card } from './ui'
import EditField from './EditField'

export default function MetadataPanel({ metadata, actions, onChange }) {
  const m = metadata || {}
  const ctx = { target_age: m.target_age }
  const set = (key) => (value) => onChange({ [key]: value })
  const seed = [m.title, m.premise].filter(Boolean).join('. ')

  return (
    <Card title="Book metadata">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <EditField label="Title" value={m.title} onChange={set('title')} />
        <EditField label="Subtitle" value={m.subtitle} onChange={set('subtitle')} />
        <EditField
          label="Tagline"
          value={m.tagline}
          onChange={set('tagline')}
          field="metadata"
          actions={actions}
          context={ctx}
          improveText={seed}
        />
        <EditField label="Series" value={m.series} onChange={set('series')} />
        <EditField label="Volume" value={m.volume} onChange={set('volume')} type="number" />
        <EditField label="Target age" value={m.target_age} onChange={set('target_age')} type="number" />
        <EditField label="Page count" value={m.page_count} onChange={set('page_count')} type="number" />
        <EditField label="Genre" value={m.genre} onChange={set('genre')} />
        <EditField label="Author" value={m.author} onChange={set('author')} />
      </div>
      <EditField
        label="Premise"
        value={m.premise}
        onChange={set('premise')}
        multiline
        rows={2}
        field="metadata"
        actions={actions}
        context={ctx}
        improveText={seed}
      />
      <EditField
        label="Dedication"
        value={m.dedication_text}
        onChange={set('dedication_text')}
        multiline
        rows={2}
      />
    </Card>
  )
}
