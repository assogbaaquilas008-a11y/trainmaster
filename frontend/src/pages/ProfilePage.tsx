import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, BookOpen, CheckCircle } from 'lucide-react'
import { attemptApi } from '../services/api'
import { useAuth } from '../store/auth'
import { format } from 'date-fns'

interface Attempt {
  id: number; quiz_id: number; score: number
  started_at: string; completed_at?: string
}

export default function ProfilePage() {
  const { user } = useAuth()
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    attemptApi.mine().then(({ data }) => setAttempts(data)).finally(() => setLoading(false))
  }, [])

  const totalPoints = attempts.reduce((s, a) => s + a.score, 0)
  const completed = attempts.filter((a) => a.completed_at).length

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Profile</h1>

      {/* User card */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center gap-5 mb-8">
        <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xl">
          {user?.username[0].toUpperCase()}
        </div>
        <div>
          <p className="text-lg font-medium text-gray-900">{user?.username}</p>
          <p className="text-sm text-gray-400">{user?.email}</p>
          {user?.is_admin && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full mt-1 inline-block">Admin</span>}
        </div>
        <div className="ml-auto flex gap-8 text-center">
          <div>
            <p className="text-2xl font-bold text-indigo-700">{totalPoints}</p>
            <p className="text-xs text-gray-400">Total points</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-800">{completed}</p>
            <p className="text-xs text-gray-400">Quizzes done</p>
          </div>
        </div>
      </div>

      {/* Attempt history */}
      <h2 className="text-lg font-medium text-gray-800 mb-4">Quiz history</h2>

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && attempts.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <BookOpen size={36} className="mx-auto mb-2 opacity-40" />
          <p>No quizzes taken yet.</p>
        </div>
      )}

      <div className="space-y-3">
        {attempts.map((a) => (
          <div
            key={a.id}
            className="bg-white border border-gray-200 rounded-xl p-4 flex items-center justify-between hover:shadow-sm transition-shadow"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">Quiz #{a.quiz_id}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {a.completed_at
                  ? `Completed ${format(new Date(a.completed_at), 'dd MMM yyyy, HH:mm')}`
                  : 'In progress'}
              </p>
            </div>
            <div className="flex items-center gap-4">
              {a.completed_at && (
                <span className="flex items-center gap-1 text-sm font-semibold text-indigo-700">
                  <CheckCircle size={14} />
                  {a.score} pts
                </span>
              )}
              <button
                onClick={() => navigate(`/quizzes/${a.quiz_id}?review=1`)}
                className="text-xs text-indigo-600 hover:underline"
              >
                Review
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
