import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Swords, Copy, Clock } from 'lucide-react'
import { duelApi, quizApi } from '../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../store/auth'

type Phase = 'lobby' | 'waiting' | 'playing' | 'result' | 'done'
interface WSMessage { type: string; [key: string]: any }

export default function DuelPage() {
  const { code } = useParams<{ code?: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [quizzes, setQuizzes] = useState<any[]>([])
  const [selectedQuiz, setSelectedQuiz] = useState<number | null>(null)
  const [inviteCode, setInviteCode] = useState(code ?? '')
  const [phase, setPhase] = useState<Phase>('lobby')
  const [wsMsg, setWsMsg] = useState<WSMessage | null>(null)
  const [answer, setAnswer] = useState('')
  const [timeLeft, setTimeLeft] = useState(0)
  const [scores, setScores] = useState({ a: 0, b: 0 })
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    quizApi.list().then(({ data }) => setQuizzes(data))
  }, [])

  // Auto-join if code in URL
  useEffect(() => {
    if (code) {
      setInviteCode(code)
      setPhase('waiting')
      connectWs(code)
    }
  }, [code]) // eslint-disable-line react-hooks/exhaustive-deps

  const connectWs = useCallback((roomCode: string) => {
    const token = localStorage.getItem('access_token')!
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${location.host}/ws/duel/${roomCode}?token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg: WSMessage = JSON.parse(e.data)
      setWsMsg(msg)

      if (msg.type === 'start') setPhase('playing')
      if (msg.type === 'question') {
        setAnswer('')
        setTimeLeft(msg.time_limit ?? 15)
        startTimer(msg.time_limit ?? 15)
      }
      if (msg.type === 'result') {
        setScores({ a: msg.score_a, b: msg.score_b })
        setPhase('result')
        clearTimer()
      }
      if (msg.type === 'game_over') {
        setPhase('done')
        clearTimer()
      }
    }

    ws.onerror = () => toast.error('WebSocket error')
    ws.onclose = () => { if (phase !== 'done') toast('Connection closed') }
  }, [phase])

  const startTimer = (seconds: number) => {
    clearTimer()
    setTimeLeft(seconds)
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { clearTimer(); return 0 }
        return t - 1
      })
    }, 1000)
  }

  const clearTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const createRoom = async () => {
    if (!selectedQuiz) return toast.error('Select a quiz first')
    try {
      const token = localStorage.getItem('access_token')!
      const { data } = await duelApi.create(selectedQuiz)
      setInviteCode(data.invite_code)
      navigate(`/duel/${data.invite_code}`)
      setPhase('waiting')
      connectWs(data.invite_code)
    } catch {
      toast.error('Could not create duel room')
    }
  }

  const submitAnswer = () => {
    if (!wsRef.current || wsMsg?.type !== 'question') return
    wsRef.current.send(JSON.stringify({
      type: 'answer',
      question_id: wsMsg.question_id,
      text: answer,
    }))
    clearTimer()
  }

  const copyCode = () => {
    navigator.clipboard.writeText(inviteCode)
    toast.success('Invite code copied!')
  }

  // ── RENDER ──────────────────────────────────────────────────────────────

  if (phase === 'done' && wsMsg) {
    const iAmA = wsMsg.winner === 'a'  // simplified; real app tracks slot
    return (
      <div className="text-center py-16">
        <Swords size={48} className="mx-auto text-indigo-500 mb-4" />
        <h1 className="text-2xl font-semibold">
          {wsMsg.winner === 'draw' ? 'Draw!' : iAmA ? 'You won! 🎉' : 'You lost'}
        </h1>
        <div className="mt-6 flex justify-center gap-12 text-lg">
          <div><p className="text-gray-500 text-sm">You</p><p className="font-bold text-2xl text-indigo-700">{scores.a}</p></div>
          <div><p className="text-gray-500 text-sm">Opponent</p><p className="font-bold text-2xl text-gray-600">{scores.b}</p></div>
        </div>
        <button onClick={() => navigate('/duel')} className="mt-8 px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700">
          Play again
        </button>
      </div>
    )
  }

  if (phase === 'lobby') {
    return (
      <div className="max-w-lg">
        <div className="flex items-center gap-3 mb-6">
          <Swords size={24} className="text-indigo-600" />
          <h1 className="text-2xl font-semibold text-gray-900">Duel Mode</h1>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-4">
          <h2 className="font-medium text-gray-800 mb-3">Create a duel</h2>
          <select
            value={selectedQuiz ?? ''}
            onChange={(e) => setSelectedQuiz(parseInt(e.target.value))}
            className="w-full border border-gray-300 rounded-xl px-3 py-2 text-sm mb-4"
          >
            <option value="">Select a quiz…</option>
            {quizzes.map((q) => <option key={q.id} value={q.id}>{q.title}</option>)}
          </select>
          <button onClick={createRoom} className="w-full py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-medium">
            Create room
          </button>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <h2 className="font-medium text-gray-800 mb-3">Join with invite code</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
              placeholder="ABCD1234"
              className="flex-1 border border-gray-300 rounded-xl px-3 py-2 text-sm font-mono"
            />
            <button
              onClick={() => { if (inviteCode.length === 8) { navigate(`/duel/${inviteCode}`); connectWs(inviteCode) } }}
              className="px-4 py-2 bg-gray-800 text-white rounded-xl text-sm hover:bg-gray-700"
            >
              Join
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (phase === 'waiting') {
    return (
      <div className="text-center py-16">
        <div className="inline-block w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-6" />
        <h2 className="text-lg font-medium text-gray-900">Waiting for opponent…</h2>
        <div className="mt-4 flex items-center justify-center gap-2 bg-gray-100 rounded-xl px-6 py-3 w-fit mx-auto">
          <span className="font-mono text-xl font-bold tracking-widest text-indigo-700">{inviteCode}</span>
          <button onClick={copyCode} className="text-gray-400 hover:text-gray-600">
            <Copy size={16} />
          </button>
        </div>
        <p className="text-sm text-gray-400 mt-3">Share this code with your opponent</p>
      </div>
    )
  }

  // Playing or result
  return (
    <div className="max-w-xl">
      {/* Scores */}
      <div className="flex justify-between mb-6 bg-white border border-gray-200 rounded-2xl p-4">
        <div className="text-center">
          <p className="text-xs text-gray-400">You</p>
          <p className="text-2xl font-bold text-indigo-700">{scores.a}</p>
        </div>
        <div className="text-sm text-gray-400 self-center font-medium">VS</div>
        <div className="text-center">
          <p className="text-xs text-gray-400">Opponent</p>
          <p className="text-2xl font-bold text-gray-600">{scores.b}</p>
        </div>
      </div>

      {phase === 'playing' && wsMsg?.type === 'question' && (
        <div className="bg-white border border-gray-200 rounded-2xl p-8">
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-400">Question</p>
            <span className={`flex items-center gap-1 font-mono font-semibold text-lg ${timeLeft <= 5 ? 'text-red-500' : 'text-gray-700'}`}>
              <Clock size={16} />{timeLeft}s
            </span>
          </div>
          <p className="text-lg font-medium text-gray-900 mb-6">{wsMsg.prompt}</p>
          <input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitAnswer()}
            autoFocus
            className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Your answer…"
          />
          <button onClick={submitAnswer} className="mt-4 w-full py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-medium">
            Submit
          </button>
        </div>
      )}

      {phase === 'result' && wsMsg?.type === 'result' && (
        <div className="bg-white border border-gray-200 rounded-2xl p-8">
          <h3 className="font-medium text-gray-900 mb-3">Round result</h3>
          <p className="text-sm text-gray-600 mb-4">
            Correct answer: <strong>{wsMsg.correct_answer}</strong>
          </p>
          <div className="grid grid-cols-2 gap-4 text-center text-sm">
            {(['a', 'b'] as const).map((slot) => (
              <div key={slot} className={`p-3 rounded-xl ${wsMsg.results?.[slot] ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                <p className="font-medium">{slot === 'a' ? 'You' : 'Opponent'}</p>
                <p className="text-xs mt-0.5">{wsMsg.answers?.[slot] || '(no answer)'}</p>
                <p className="font-semibold mt-1">{wsMsg.results?.[slot] ? '✓ Correct' : '✗ Wrong'}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 text-center mt-4">Next question in a moment…</p>
        </div>
      )}
    </div>
  )
}
