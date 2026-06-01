import { useEffect, useMemo, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Save, Undo2, BookUp, Loader2, ArrowLeft } from 'lucide-react'
import { api } from '../services/api'
import { Card } from '../components/ui'
import EditField from '../components/EditField'
import MetadataPanel from '../components/MetadataPanel'
import ChapterCard from '../components/ChapterCard'
import ExperimentPanel from '../components/ExperimentPanel'
import BiographyPanel from '../components/BiographyPanel'
import RawJsonTab from '../components/RawJsonTab'
import ChatPanel from '../components/ChatPanel'

export default function BookEditor() {
  const [params] = useSearchParams()
  const project = params.get('project')

  const [book, setBook] = useState(null)
  const [actions, setActions] = useState({})
  const [dirty, setDirty] = useState(false)
  const [tab, setTab] = useState('structured')
  const [collapsed, setCollapsed] = useState({})
  const [saveErrors, setSaveErrors] = useState(null)
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!project) return
    api.getActions().then(setActions).catch(() => {})
    setDirty(false)
    api
      .getBook(project)
      .then(setBook)
      .catch((e) => setNotice(`Failed to load: ${e.message}`))
  }, [project])

  const update = (fn) => {
    setBook((b) => fn(structuredClone(b)))
    setDirty(true)
  }

  const targetAge = book?.metadata?.target_age
  const characters = useMemo(() => book?.characters_used || [], [book])

  const save = async () => {
    setBusy(true)
    setSaveErrors(null)
    setNotice(null)
    try {
      await api.saveBook(project, book)
      setDirty(false)
      setNotice('Saved ✓')
    } catch (e) {
      const detail = e.response?.data?.detail
      if (Array.isArray(detail)) setSaveErrors(detail)
      else setNotice(`Save failed: ${detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const discard = () => {
    api.getBook(project).then((b) => {
      setBook(b)
      setDirty(false)
      setSaveErrors(null)
    })
  }

  const publish = async () => {
    setBusy(true)
    setNotice('Rendering PDF/EPUB…')
    try {
      const res = await api.publish(project, ['pdf', 'epub'])
      setNotice(`Published: ${Object.values(res.outputs).join(', ')}`)
    } catch (e) {
      setNotice(`Publish failed: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  if (!project) return <Empty>No project selected.</Empty>
  if (!book) return <Empty>Loading…</Empty>

  return (
    <div className="flex h-full flex-col">
      <Toolbar
        title={book.metadata?.title}
        dirty={dirty}
        busy={busy}
        tab={tab}
        setTab={setTab}
        onSave={save}
        onDiscard={discard}
        onPublish={publish}
      />

      {notice && (
        <div className="border-b border-primary-100 bg-primary-50 px-6 py-2 text-sm text-primary-800">
          {notice}
        </div>
      )}
      {saveErrors && (
        <div className="border-b border-red-100 bg-red-50 px-6 py-2 text-sm text-red-800">
          <p className="font-medium">Validation failed — fix these and save again:</p>
          <ul className="list-disc pl-5">
            {saveErrors.map((err, i) => (
              <li key={i}>
                <code>{(err.loc || []).join('.')}</code>: {err.msg}
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === 'json' ? (
        <RawJsonTab
          book={book}
          onApply={(parsed) => {
            setBook(parsed)
            setDirty(true)
            setTab('structured')
          }}
        />
      ) : (
        <div className="scrollbar-thin flex-1 space-y-6 overflow-auto p-6">
          <MetadataPanel
            metadata={book.metadata}
            actions={actions}
            onChange={(patch) =>
              update((b) => ({ ...b, metadata: { ...b.metadata, ...patch } }))
            }
          />

          {(book.chapters || []).map((ch, i) => (
            <ChapterCard
              key={i}
              chapter={ch}
              project={project}
              characters={characters}
              targetAge={targetAge}
              actions={actions}
              collapsed={!!collapsed[i]}
              onToggle={() => setCollapsed((c) => ({ ...c, [i]: !c[i] }))}
              onChange={(patch) =>
                update((b) => ({
                  ...b,
                  chapters: b.chapters.map((c, j) => (j === i ? { ...c, ...patch } : c)),
                }))
              }
            />
          ))}

          <ExperimentPanel
            experiment={book.experiment}
            targetAge={targetAge}
            actions={actions}
            onChange={(patch) =>
              update((b) => ({ ...b, experiment: { ...b.experiment, ...patch } }))
            }
          />

          <BiographyPanel
            biography={book.biography}
            targetAge={targetAge}
            actions={actions}
            onChange={(patch) =>
              update((b) => ({ ...b, biography: { ...b.biography, ...patch } }))
            }
          />

          {book.back_matter_for_parents !== undefined && (
            <Card title="For parents & educators">
              <EditField
                label="Back matter"
                value={book.back_matter_for_parents}
                onChange={(v) => update((b) => ({ ...b, back_matter_for_parents: v }))}
                multiline
                rows={5}
              />
            </Card>
          )}
        </div>
      )}

      <ChatPanel project={project} />
    </div>
  )
}

function Toolbar({ title, dirty, busy, tab, setTab, onSave, onDiscard, onPublish }) {
  return (
    <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-6 py-3">
      <Link to="/" className="text-gray-400 hover:text-gray-700" title="Back to library">
        <ArrowLeft size={18} />
      </Link>
      <h1 className="truncate text-lg font-semibold text-gray-800">{title}</h1>
      {dirty && <span className="h-2 w-2 rounded-full bg-amber-500" title="Unsaved changes" />}

      <div className="ml-4 flex rounded-lg border border-gray-200 p-0.5 text-sm">
        {['structured', 'json'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={
              'rounded-md px-3 py-1 ' +
              (tab === t ? 'bg-primary-600 text-white' : 'text-gray-600 hover:bg-gray-50')
            }
          >
            {t === 'structured' ? 'Editor' : 'Raw JSON'}
          </button>
        ))}
      </div>

      <div className="ml-auto flex gap-2">
        <button
          onClick={onDiscard}
          disabled={busy || !dirty}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <Undo2 size={15} /> Discard
        </button>
        <button
          onClick={onPublish}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <BookUp size={15} />}
          Re-publish
        </button>
        <button
          onClick={onSave}
          disabled={busy || !dirty}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          Save
        </button>
      </div>
    </header>
  )
}

function Empty({ children }) {
  return <div className="flex h-full items-center justify-center text-gray-400">{children}</div>
}
