import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuth } from './store/auth'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import QuizPage from './pages/QuizPage'
import LeaderboardPage from './pages/LeaderboardPage'
import ProfilePage from './pages/ProfilePage'
import DuelPage from './pages/DuelPage'
import AdminPage from './pages/AdminPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <div className="flex h-screen items-center justify-center text-gray-500">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }: { children: JSX.Element }) {
  const { user } = useAuth()
  if (!user?.is_admin) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const hydrate = useAuth((s) => s.hydrate)
  useEffect(() => { hydrate() }, [hydrate])

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index                   element={<DashboardPage />} />
          <Route path="quizzes/:id"      element={<QuizPage />} />
          <Route path="leaderboard"      element={<LeaderboardPage />} />
          <Route path="profile"          element={<ProfilePage />} />
          <Route path="duel/:code?"      element={<DuelPage />} />
          <Route path="admin/*"          element={
            <RequireAdmin><AdminPage /></RequireAdmin>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
