import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Trophy, User, Swords, ShieldCheck, LogOut
} from 'lucide-react'
import { useAuth } from '../store/auth'
import clsx from 'clsx'

const navItems = [
  { to: '/',            label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  { to: '/duel',        label: 'Duel',        icon: Swords },
  { to: '/profile',     label: 'Profile',     icon: User },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <aside className="w-56 flex flex-col bg-white border-r border-gray-200 py-6">
        <div className="px-6 mb-8">
          <span className="text-xl font-semibold text-indigo-700">TrainMaster</span>
          <p className="text-xs text-gray-400 mt-0.5">{user?.username}</p>
        </div>

        <nav className="flex-1 px-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}

          {user?.is_admin && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-amber-50 text-amber-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                )
              }
            >
              <ShieldCheck size={16} />
              Admin
            </NavLink>
          )}
        </nav>

        <div className="px-3 mt-auto">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-100 transition-colors"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
