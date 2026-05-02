import { useEffect, useState } from 'react'
import { Trophy } from 'lucide-react'
import { leaderboardApi } from '../services/api'
import { useAuth } from '../store/auth'

interface Row {
  rank: number; user_id: number; username: string
  total_points: number; quizzes_taken: number; correct_answers: number
}

const medals = ['🥇', '🥈', '🥉']

export default function LeaderboardPage() {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()

  useEffect(() => {
    leaderboardApi.get().then(({ data }) => setRows(data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-400">Loading…</p>

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Trophy size={24} className="text-amber-500" />
        <h1 className="text-2xl font-semibold text-gray-900">Global Leaderboard</h1>
      </div>

      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left px-5 py-3 text-gray-500 font-medium w-12">#</th>
              <th className="text-left px-5 py-3 text-gray-500 font-medium">Player</th>
              <th className="text-right px-5 py-3 text-gray-500 font-medium">Points</th>
              <th className="text-right px-5 py-3 text-gray-500 font-medium hidden sm:table-cell">Quizzes</th>
              <th className="text-right px-5 py-3 text-gray-500 font-medium hidden sm:table-cell">Correct</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.user_id}
                className={`border-b border-gray-50 last:border-0 transition-colors ${
                  row.user_id === user?.id ? 'bg-indigo-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-5 py-3 text-center">
                  {row.rank <= 3 ? medals[row.rank - 1] : <span className="text-gray-400">{row.rank}</span>}
                </td>
                <td className="px-5 py-3 font-medium text-gray-900">
                  {row.username}
                  {row.user_id === user?.id && (
                    <span className="ml-2 text-xs text-indigo-500 font-normal">(you)</span>
                  )}
                </td>
                <td className="px-5 py-3 text-right font-semibold text-indigo-700">
                  {row.total_points.toLocaleString()}
                </td>
                <td className="px-5 py-3 text-right text-gray-500 hidden sm:table-cell">
                  {row.quizzes_taken}
                </td>
                <td className="px-5 py-3 text-right text-gray-500 hidden sm:table-cell">
                  {row.correct_answers}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows.length === 0 && (
          <p className="text-center py-12 text-gray-400">No scores yet. Be the first!</p>
        )}
      </div>
    </div>
  )
}
