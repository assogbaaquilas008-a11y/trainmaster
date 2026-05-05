import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Trophy, User, Swords, ShieldCheck, LogOut, Menu, X
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
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)
  const closeSidebar = () => setSidebarOpen(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="relative min-h-screen bg-gray-50 font-sans">
      {/* Overlay sombre quand le menu est ouvert (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Bouton hamburger – toujours visible */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 rounded-md bg-white shadow-md hover:bg-gray-100 focus:outline-none"
        aria-label="Menu"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar latérale */}
      <aside
        className={`
          fixed top-0 left-0 z-30 h-full w-64 bg-white shadow-lg transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* En-tête du sidebar avec fermeture sur mobile */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
          <div>
            <span className="text-xl font-semibold text-indigo-700">TrainMaster</span>
            <p className="text-xs text-gray-400 mt-0.5">{user?.username}</p>
          </div>
          <button
            onClick={toggleSidebar}
            className="p-1 rounded-md hover:bg-gray-100 md:hidden"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={closeSidebar}
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
              onClick={closeSidebar}
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

        {/* Bouton de déconnexion */}
        <div className="px-3 pb-6">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-100 transition-colors"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>

      {/* Contenu principal – décalé uniquement sur desktop si menu fixe */}
      <main
        className={`
          transition-all duration-300
          ${sidebarOpen ? 'md:ml-64' : ''}
        `}
      >
        <div className="max-w-4xl mx-auto p-8 pt-16 md:pt-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}