import { useEffect, useState } from 'react'
import { adminApi } from '../services/api'
import { ShieldCheck, Plus, Upload, Flag, BarChart2, Users } from 'lucide-react'
import toast from 'react-hot-toast'

type Tab = 'stats' | 'quizzes' | 'flags' | 'users'

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('stats')
  const [stats, setStats] = useState<any>(null)
  const [quizzes, setQuizzes] = useState<any[]>([])
  const [flags, setFlags] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])

  // Create quiz form state
  const [title, setTitle] = useState('')
  const [timer, setTimer] = useState(30)
  const [questions, setQuestions] = useState([{ prompt: '', correct_answer: '', alt_answers: '' }])
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  useEffect(() => {
    adminApi.stats().then(({ data }) => setStats(data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'quizzes') adminApi.listQuizzes().then(({ data }) => setQuizzes(data))
    if (tab === 'flags') adminApi.listFlags().then(({ data }) => setFlags(data))
    if (tab === 'users') adminApi.listUsers().then(({ data }) => setUsers(data))
  }, [tab])

  const createQuiz = async () => {
    if (!title.trim()) return toast.error('Title required')
    try {
      await adminApi.createQuiz({
        title, timer_seconds: timer,
        questions: questions.map((q, i) => ({ ...q, position: i }))
      })
      toast.success('Quiz created!')
      setTitle('')
      setQuestions([{ prompt: '', correct_answer: '', alt_answers: '' }])
      adminApi.listQuizzes().then(({ data }) => setQuizzes(data))
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? 'Error')
    }
  }

  const uploadQuiz = async () => {
    if (!uploadFile) return toast.error('Select a file')
    try {
      await adminApi.uploadQuiz(uploadFile)
      toast.success('Quiz uploaded!')
      setUploadFile(null)
      adminApi.listQuizzes().then(({ data }) => setQuizzes(data))
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? 'Upload failed')
    }
  }

  const reviewFlag = async (id: number, status: 'accepted' | 'rejected') => {
    try {
      await adminApi.reviewFlag(id, { status })
      toast.success(`Flag ${status}`)
      setFlags((f) => f.filter((x) => x.id !== id))
    } catch {
      toast.error('Error reviewing flag')
    }
  }

  const deleteQuiz = async (id: number) => {
    if (!confirm('Soft-delete this quiz?')) return
    await adminApi.deleteQuiz(id)
    setQuizzes((q) => q.filter((x) => x.id !== id))
    toast.success('Quiz removed')
  }

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'stats',   label: 'Stats',   icon: BarChart2 },
    { id: 'quizzes', label: 'Quizzes', icon: Plus },
    { id: 'flags',   label: 'Flags',   icon: Flag },
    { id: 'users',   label: 'Users',   icon: Users },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <ShieldCheck size={24} className="text-amber-600" />
        <h1 className="text-2xl font-semibold text-gray-900">Admin Panel</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-8 w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Stats */}
      {tab === 'stats' && stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            ['Users',    stats.total_users],
            ['Quizzes',  stats.total_quizzes],
            ['Attempts', stats.total_attempts],
            ['Pending flags', stats.pending_flags],
          ].map(([label, value]) => (
            <div key={label as string} className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-gray-400 mb-1">{label}</p>
              <p className="text-3xl font-semibold text-gray-900">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Quizzes */}
      {tab === 'quizzes' && (
        <div className="space-y-8">
          {/* Create form */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="font-medium text-gray-800 mb-4">Create quiz</h2>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Quiz title"
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm mb-3"
            />
            <div className="flex items-center gap-3 mb-4">
              <label className="text-sm text-gray-500">Timer (s):</label>
              <input
                type="number" min={5} max={300}
                value={timer}
                onChange={(e) => setTimer(parseInt(e.target.value))}
                className="w-20 border border-gray-200 rounded-lg px-2 py-1 text-sm"
              />
            </div>

            {questions.map((q, i) => (
              <div key={i} className="border border-gray-100 rounded-xl p-4 mb-3 space-y-2">
                <p className="text-xs text-gray-400">Question {i + 1}</p>
                <input
                  value={q.prompt}
                  onChange={(e) => setQuestions(qs => qs.map((x, j) => j === i ? { ...x, prompt: e.target.value } : x))}
                  placeholder="Question prompt"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
                <input
                  value={q.correct_answer}
                  onChange={(e) => setQuestions(qs => qs.map((x, j) => j === i ? { ...x, correct_answer: e.target.value } : x))}
                  placeholder="Correct answer"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
                <input
                  value={q.alt_answers}
                  onChange={(e) => setQuestions(qs => qs.map((x, j) => j === i ? { ...x, alt_answers: e.target.value } : x))}
                  placeholder="Alternative answers (pipe-separated: ans1|ans2)"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            ))}

            <div className="flex gap-2 mt-2">
              <button
                onClick={() => setQuestions(qs => [...qs, { prompt: '', correct_answer: '', alt_answers: '' }])}
                className="text-sm px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                + Add question
              </button>
              <button onClick={createQuiz} className="text-sm px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium">
                Create
              </button>
            </div>
          </div>

          {/* Upload JSON */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="font-medium text-gray-800 mb-3 flex items-center gap-2">
              <Upload size={16} /> Upload JSON quiz
            </h2>
            <p className="text-xs text-gray-400 mb-3">
              Format: <code className="bg-gray-100 px-1 rounded">{"{ title, timer_seconds, questions: [{prompt, correct_answer, alt_answers}] }"}</code>
            </p>
            <div className="flex gap-2">
              <input
                type="file" accept=".json"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                className="text-sm text-gray-500"
              />
              <button onClick={uploadQuiz} className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm hover:bg-gray-700">
                Upload
              </button>
            </div>
          </div>

          {/* Quiz list */}
          <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-gray-500 font-medium">Title</th>
                <th className="text-center px-5 py-3 text-gray-500 font-medium">Questions</th>
                <th className="text-center px-5 py-3 text-gray-500 font-medium">Active</th>
                <th className="px-5 py-3" />
              </tr></thead>
              <tbody>
                {quizzes.map((q) => (
                  <tr key={q.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-5 py-3 font-medium text-gray-900">{q.title}</td>
                    <td className="px-5 py-3 text-center text-gray-500">{q.questions?.length ?? 0}</td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${q.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {q.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => deleteQuiz(q.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Flags */}
      {tab === 'flags' && (
        <div className="space-y-3">
          {flags.length === 0 && <p className="text-gray-400 text-sm">No pending flags.</p>}
          {flags.map((flag) => (
            <div key={flag.id} className="bg-white border border-amber-200 rounded-2xl p-5">
              <p className="text-xs text-gray-400 mb-1">Question #{flag.question_id}</p>
              <p className="font-medium text-gray-900 mb-1">Submitted: <em>{flag.submitted_text}</em></p>
              {flag.reason && <p className="text-sm text-gray-500 mb-3">Reason: {flag.reason}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => reviewFlag(flag.id, 'accepted')}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Accept + award points
                </button>
                <button
                  onClick={() => reviewFlag(flag.id, 'rejected')}
                  className="px-4 py-2 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Users */}
      {tab === 'users' && (
        <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-100">
              <th className="text-left px-5 py-3 text-gray-500 font-medium">Username</th>
              <th className="text-left px-5 py-3 text-gray-500 font-medium">Email</th>
              <th className="text-center px-5 py-3 text-gray-500 font-medium">Admin</th>
            </tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-5 py-3 font-medium text-gray-900">{u.username}</td>
                  <td className="px-5 py-3 text-gray-500">{u.email}</td>
                  <td className="px-5 py-3 text-center">
                    {u.is_admin && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Admin</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
