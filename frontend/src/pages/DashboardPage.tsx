import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, CheckCircle, Clock } from 'lucide-react'
import { quizApi, attemptApi } from '../services/api'
import toast from 'react-hot-toast'

interface Quiz {
  id: number
  title: string
  description?: string
  timer_seconds: number
  question_count: number
}

interface Attempt {
  quiz_id: number
  completed_at?: string
  score: number
}

export default function DashboardPage() {
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [attempts, setAttempts] = useState<Map<number, Attempt>>(new Map())
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([quizApi.list(), attemptApi.mine()])
      .then(([qRes, aRes]) => {
        setQuizzes(qRes.data)
        const map = new Map<number, Attempt>()
        aRes.data.forEach((a: Attempt) => map.set(a.quiz_id, a))
        setAttempts(map)
      })
      .catch(() => toast.error('Failed to load quizzes'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-400">Loading quizzes…</p>

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">Quizzes</h1>
      <p className="text-gray-500 mb-6 text-sm">Each quiz can only be taken once for score.</p>

      {quizzes.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <BookOpen size={40} className="mx-auto mb-3 opacity-40" />
          <p>No quizzes yet. Check back soon!</p>
        </div>
      )}

      <div className="grid gap-4">
        {quizzes.map((quiz) => {
          const attempt = attempts.get(quiz.id)
          const done = !!attempt?.completed_at

          return (
            <div
              key={quiz.id}
              className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between hover:shadow-sm transition-shadow"
            >
              <div className="flex-1 min-w-0">
                <h2 className="font-medium text-gray-900 truncate">{quiz.title}</h2>
                {quiz.description && (
                  <p className="text-sm text-gray-500 mt-0.5 truncate">{quiz.description}</p>
                )}
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <BookOpen size={12} />
                    {quiz.question_count} questions
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {quiz.timer_seconds}s per question
                  </span>
                  {done && (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle size={12} />
                      {attempt.score} pts
                    </span>
                  )}
                </div>
              </div>

              <div className="ml-4 flex gap-2 shrink-0">
                {done ? (
                  <button
                    onClick={() => navigate(`/quizzes/${quiz.id}?review=1`)}
                    className="px-4 py-2 text-sm text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
                  >
                    Review
                  </button>
                ) : (
                  <button
                    onClick={() => navigate(`/quizzes/${quiz.id}`)}
                    className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    Take quiz
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
