import { useState } from 'react'
import { Trash2, Wand2, Loader2 } from 'lucide-react'
import { Label, TextInput } from './ui'
import EditField from './EditField'
import ImageCompareModal from './ImageCompareModal'
import { api } from '../services/api'

const PLACEMENTS = ['full_page', 'inline', 'header', 'footer']

export default function IllustrationCard({
  illustration,
  project,
  chapterNumber,
  index,
  ctx,
  actions,
  onChange,
  onRemove,
}) {
  const ill = illustration || {}
  const set = (key) => (value) => onChange({ [key]: value })

  const [bust, setBust] = useState(0)
  const [busy, setBusy] = useState(false) // generating a candidate
  const [resolving, setResolving] = useState(false) // accepting / discarding
  const [error, setError] = useState(null)
  const [useRef, setUseRef] = useState(false)
  const [candidate, setCandidate] = useState(null) // { path, prompt }

  const targetPath = ill.image_path || `illustrations/chapter_${chapterNumber}_ill_${index + 1}.png`
  const imgSrc = ill.image_path
    ? `${api.mediaUrl(project, ill.image_path)}${bust ? `&t=${bust}` : ''}`
    : null

  const regenerate = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await api.regenerateImage(project, {
        target: targetPath,
        prompt: ill.description || '',
        scene_context: ill.scene_context || '',
        characters: ill.characters || [],
        target_age: ctx?.target_age ?? 7,
        use_current_as_reference: useRef && !!ill.image_path,
      })
      setCandidate({ path: res.candidate, prompt: res.prompt })
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setBusy(false)
    }
  }

  const accept = async () => {
    setResolving(true)
    try {
      const res = await api.acceptImage(project, { candidate: candidate.path, target: targetPath })
      if (res.image_path !== ill.image_path) set('image_path')(res.image_path)
      setBust(Date.now())
      setCandidate(null)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setResolving(false)
    }
  }

  const reject = async () => {
    setResolving(true)
    try {
      await api.discardImage(project, { candidate: candidate.path })
    } catch {
      // a leftover candidate is harmless; closing the modal is what matters
    } finally {
      setCandidate(null)
      setResolving(false)
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <div className="flex gap-4">
        <div className="flex-none">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={ill.caption || 'illustration'}
              className="h-28 w-28 rounded-md border border-gray-200 object-cover"
              onError={(e) => {
                e.currentTarget.style.visibility = 'hidden'
              }}
            />
          ) : (
            <div className="flex h-28 w-28 items-center justify-center rounded-md border border-dashed border-gray-300 text-center text-xs text-gray-400">
              no image yet
            </div>
          )}

          <button
            onClick={regenerate}
            disabled={busy || resolving || !(ill.description || '').trim()}
            title="Generate with the configured image model"
            className="mt-2 inline-flex w-28 items-center justify-center gap-1 rounded-md border border-primary-200 bg-primary-50 px-2 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 disabled:opacity-50"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Wand2 size={12} />}
            {ill.image_path ? 'Regenerate' : 'Generate'}
          </button>
          {ill.image_path && (
            <label className="mt-1 flex w-28 items-center gap-1 text-[11px] text-gray-500">
              <input type="checkbox" checked={useRef} onChange={(e) => setUseRef(e.target.checked)} />
              use as reference
            </label>
          )}
          {error && <p className="mt-1 w-28 break-words text-[11px] text-red-600">{String(error)}</p>}
        </div>

        <div className="flex-1 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label>Page</Label>
              <TextInput value={ill.page} onChange={set('page')} type="number" />
            </div>
            <div className="space-y-1.5">
              <Label>Placement</Label>
              <select
                value={ill.placement || 'inline'}
                onChange={(e) => set('placement')(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              >
                {PLACEMENTS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end justify-end">
              <button
                onClick={onRemove}
                title="Remove illustration"
                className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-2 text-xs text-red-700 hover:bg-red-100"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <EditField
            label="Description (image prompt)"
            value={ill.description}
            onChange={set('description')}
            multiline
            rows={3}
            field="image_prompt"
            actions={actions}
            context={ctx}
          />
          <EditField
            label="Caption"
            value={ill.caption}
            onChange={set('caption')}
            field="caption"
            actions={actions}
            context={ctx}
            improveText={ill.description}
          />
          <EditField label="Scene context" value={ill.scene_context} onChange={set('scene_context')} />
          <EditField
            label="Characters (comma-separated)"
            value={(ill.characters || []).join(', ')}
            onChange={(v) =>
              set('characters')(
                v
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </div>
      </div>

      {candidate && (
        <ImageCompareModal
          project={project}
          currentPath={ill.image_path}
          candidatePath={candidate.path}
          caption={candidate.prompt}
          busy={resolving}
          onAccept={accept}
          onReject={reject}
        />
      )}
    </div>
  )
}
