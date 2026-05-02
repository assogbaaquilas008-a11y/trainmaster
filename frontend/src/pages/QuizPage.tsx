import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { AlertTriangle, CheckCircle, Clock, XCircle } from 'lucide-react'
import { flagApi, quizApi } from '../services/api'
import toast from 'react-hot-toast'

interface Question { id: number; prompt: string; position: number }
interface Quiz { id: number; title: string; timer_seconds: number; questions: Question[] }
interface ValidationResult {
  question_id: number; is_correct: boolean; confidence: number
  method: string; correct_answer: string; points_awarded: number
}

type Phase = 'loading' | 'playing' | 'result' | 'review' | 'done'

export default function QuizPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const isReview = searchParams.get('review') === '1'
  const navigate = useNavigate()

  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [qIndex, setQIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [lastResult, setLastResult] = useState<ValidationResult | null>(null)
  const [timeLeft, setTimeLeft] = useState(0)
  const [totalScore, setTotalScore] = useState(0)
  const [attemptId, setAttemptId] = useState<number | null>(null)
  const [flagReason, setFlagReason] = useState('')
  const [flagging, setFlagging] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const quizId = parseInt(id!)

  // Load quiz
  useEffect(() => {
    quizApi.get(quizId).then(({ data }) => {
      setQuiz(data)
      if (isReview) {
        setPhase('review')
      } else {
        setPhase('playing')
      }
    }).catch(() => {
      toast.error('Quiz not found')
      navigate('/')
    })
  }, [quizId, isReview, navigate])

  // Start attempt when entering play mode
  useEffect(() => {
    if (phase !== 'playing' || !quiz) return
    quizApi.start(quizId)
      .then(({ data }) => setAttemptId(data.id))
      .catch((e) => {
        if (e.response?.status === 409) {
          toast.error('Already attempted – redirecting to review')
          navigate(`/quizzes/${quizId}?review=1`)
        } else {
          toast.error('Could not start quiz')
          navigate('/')
        }
      })
  }, [phase, quiz, quizId, navigate])

  // Timer
  const startTimer = useCallback(() => {
    if (!quiz) return
    setTimeLeft(quiz.timer_seconds)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current!)
          handleSubmit(true)  // time expired
          return 0
        }
        return t - 1
      })
    }, 1000)
  }, [quiz])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (phase === 'playing' && attemptId && quiz) {
      startTimer()
      inputRef.current?.focus()
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [qIndex, phase, attemptId, quiz, startTimer])

  const handleSubmit = async (expired = false) => {
    if (timerRef.current) clearInterval(timerRef.current)
    const text = expired ? '' : answer.trim()
    try {
      const { data }: { data: ValidationResult } = await quizApi.answer(quizId, {
        question_id: quiz!.questions[qIndex].id,
        submitted_text: text,
      })
      setLastResult(data)
      if (data.is_correct) setTotalScore((s) => s + data.points_awarded)
      setPhase('result')
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? 'Error submitting answer')
    }
  }

  const nextQuestion = async () => {
    const nextIdx = qIndex + 1
    if (nextIdx >= (quiz?.questions.length ?? 0)) {
      // Finish
      await quizApi.finish(quizId)
      setPhase('done')
    } else {
      setAnswer('')
      setLastResult(null)
      setQIndex(nextIdx)
      setPhase('playing')
    }
  }

  const submitFlag = async () => {
    if (!lastResult) return
    setFlagging(true)
    try {
      await flagApi.create({
        question_id: lastResult.question_id,
        submitted_text: answer,
        reason: flagReason,
      })
      toast.success('Flag submitted – admin will review')
      setFlagReason('')
    } catch {
      toast.error('Could not submit flag')
    } finally {
      setFlagging(false)
    }
  }

  if (!quiz || phase === 'loading') {
    return <p className="text-gray-400">Loading…</p>
  }

  if (phase === 'review') {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">{quiz.title} – Review</h1>
        <div className="space-y-4">
          {quiz.questions.map((q, i) => (
            <div key={q.id} className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-xs text-gray-400 mb-1">Question {i + 1}</p>
              <p className="font-medium text-gray-900">{q.prompt}</p>
            </div>
          ))}
        </div>
        <button onClick={() => navigate('/')} className="mt-6 text-sm text-indigo-600 hover:underline">
          ← Back to dashboard
        </button>
      </div>
    )
  }

  if (phase === 'done') {
    return (
      <div className="text-center py-16">
        <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
        <h1 className="text-2xl font-semibold text-gray-900">Quiz complete!</h1>
        <p className="text-4xl font-bold text-indigo-600 mt-4">{totalScore} pts</p>
        <button
          onClick={() => navigate('/')}
          className="mt-8 px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors"
        >
          Back to dashboard
        </button>
      </div>
    )
  }

  const question = quiz.questions[qIndex]
  const progress = ((qIndex) / quiz.questions.length) * 100

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{quiz.title}</h1>
          <p className="text-sm text-gray-400">
            Question {qIndex + 1} of {quiz.questions.length}
          </p>
        </div>
        {phase === 'playing' && (
          <div className={`flex items-center gap-2 text-lg font-mono font-semibold ${timeLeft <= 5 ? 'text-red-500' : 'text-gray-700'}`}>
            <Clock size={18} />
            {timeLeft}s
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-100 rounded-full mb-8 overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Question */}
      <div className="bg-white border border-gray-200 rounded-2xl p-8">
        <p className="text-lg font-medium text-gray-900 mb-6">{question.prompt}</p>

        {phase === 'playing' && (
          <div>
            <input
              ref={inputRef}
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="Type your answer…"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={() => handleSubmit()}
              className="mt-4 w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors"
            >
              Submit
            </button>
          </div>
        )}

        {phase === 'result' && lastResult && (
          <div>
            {/* Result banner */}
            <div className={`flex items-center gap-3 p-4 rounded-xl mb-4 ${lastResult.is_correct ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
              {lastResult.is_correct
                ? <CheckCircle size={20} />
                : <XCircle size={20} />}
              <div>
                <p className="font-medium">
                  {lastResult.is_correct ? `Correct! +${lastResult.points_awarded} pts` : 'Incorrect'}
                </p>
                <p className="text-sm opacity-75">
                  Correct answer: <strong>{lastResult.correct_answer}</strong>
                </p>
              </div>
            </div>

            {/* Flag option for wrong answers */}
            {!lastResult.is_correct && (
              <details className="mb-4">
                <summary className="flex items-center gap-2 text-sm text-amber-600 cursor-pointer hover:text-amber-700">
                  <AlertTriangle size={14} />
                  Think your answer should be accepted? Flag it
                </summary>
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-gray-500">Your submitted answer: <em>{answer}</em></p>
                  <input
                    type="text"
                    value={flagReason}
                    onChange={(e) => setFlagReason(e.target.value)}
                    placeholder="Reason (optional)"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <button
                    onClick={submitFlag}
                    disabled={flagging}
                    className="text-sm px-4 py-2 border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-50 transition-colors disabled:opacity-50"
                  >
                    {flagging ? 'Submitting…' : 'Submit flag'}
                  </button>
                </div>
              </details>
            )}

            <button
              onClick={nextQuestion}
              className="w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors"
            >
              {qIndex + 1 >= quiz.questions.length ? 'Finish quiz' : 'Next question →'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
