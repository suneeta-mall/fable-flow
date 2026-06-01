import { ChevronDown, ChevronRight, Plus } from 'lucide-react'
import { Label, TextInput } from './ui'
import EditField from './EditField'
import ImproveMenu from './ImproveMenu'
import IllustrationCard from './IllustrationCard'

const BLANK_ILLUSTRATION = {
  page: 1,
  placement: 'inline',
  description: '',
  caption: null,
  characters: [],
  scene_context: '',
  image_path: null,
}

export default function ChapterCard({
  chapter,
  project,
  characters,
  targetAge,
  actions,
  onChange,
  collapsed,
  onToggle,
}) {
  const ch = chapter || {}
  const ctx = { target_age: targetAge, chapter_title: ch.title, characters }
  const set = (key) => (value) => onChange({ [key]: value })

  const questions = ch.reflection?.questions || ['', '', '']
  const setQuestion = (i) => (value) =>
    onChange({ reflection: { questions: questions.map((q, j) => (j === i ? value : q)) } })

  const illustrations = ch.illustrations || []
  const setIllustration = (i, patch) =>
    set('illustrations')(illustrations.map((il, j) => (j === i ? { ...il, ...patch } : il)))
  const addIllustration = () =>
    set('illustrations')([...illustrations, { ...BLANK_ILLUSTRATION, page: ch.page_start || 1 }])
  const removeIllustration = (i) => set('illustrations')(illustrations.filter((_, j) => j !== i))

  return (
    <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-2 px-5 py-3 text-left text-sm font-semibold text-gray-700"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        Chapter {ch.number}: {ch.title || <span className="text-gray-400">(untitled)</span>}
        <span className="ml-auto text-xs font-normal text-gray-400">
          pp. {ch.page_start}–{ch.page_end} · {illustrations.length} illus
        </span>
      </button>

      {!collapsed && (
        <div className="space-y-4 border-t border-gray-100 p-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="md:col-span-2">
              <EditField label="Title" value={ch.title} onChange={set('title')} />
            </div>
            <div className="space-y-1.5">
              <Label>Page start</Label>
              <TextInput value={ch.page_start} onChange={set('page_start')} type="number" />
            </div>
            <div className="space-y-1.5">
              <Label>Page end</Label>
              <TextInput value={ch.page_end} onChange={set('page_end')} type="number" />
            </div>
          </div>

          <EditField
            label="Text"
            value={ch.text}
            onChange={set('text')}
            multiline
            rows={14}
            field="prose"
            actions={actions}
            context={ctx}
          />

          <EditField
            label="Poem"
            value={ch.poem}
            onChange={set('poem')}
            multiline
            rows={5}
            field="poem"
            actions={actions}
            context={ctx}
          />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Reflection questions</Label>
              <ImproveMenu
                field="reflection"
                text={ch.text}
                context={ctx}
                actions={actions}
                onAccept={(result) =>
                  onChange({ reflection: { questions: result.slice(0, 3) } })
                }
              />
            </div>
            {[0, 1, 2].map((i) => (
              <TextInput key={i} value={questions[i] || ''} onChange={setQuestion(i)} />
            ))}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Illustrations</Label>
              <button
                onClick={addIllustration}
                className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                <Plus size={13} /> Add
              </button>
            </div>
            {illustrations.map((il, i) => (
              <IllustrationCard
                key={i}
                illustration={il}
                project={project}
                chapterNumber={ch.number}
                index={i}
                ctx={ctx}
                actions={actions}
                onChange={(patch) => setIllustration(i, patch)}
                onRemove={() => removeIllustration(i)}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
