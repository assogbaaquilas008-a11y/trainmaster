import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await register(username, email, password)
      navigate('/')
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-indigo-700">TrainMaster</h1>
          <p className="text-gray-500 mt-1 text-sm">Create your account</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm">
          <h2 className="text-lg font-medium text-gray-900 mb-6">Register</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Username</label>
              <input
                type="text" required minLength={3} value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Email</label>
              <input
                type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Password</label>
              <input
                type="password" required minLength={8} value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-600 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
