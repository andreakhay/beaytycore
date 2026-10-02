import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const icons = {
  dash: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="1" width="6" height="6" rx="0.5"/><rect x="9" y="1" width="6" height="6" rx="0.5"/><rect x="1" y="9" width="6" height="6" rx="0.5"/><rect x="9" y="9" width="6" height="6" rx="0.5"/></svg>,
  cal:  <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="2" width="14" height="13" rx="1"/><line x1="5" y1="1" x2="5" y2="4"/><line x1="11" y1="1" x2="11" y2="4"/><line x1="1" y1="6" x2="15" y2="6"/></svg>,
  nail: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M8 2c-2 0-4 1.5-4 5v5a2 2 0 004 0V7"/><path d="M8 2c2 0 4 1.5 4 5v5a2 2 0 01-4 0V7"/></svg>,
  hair: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M5 2c0 4 2 6 3 8"/><path d="M8 2c0 4 1 6 2 8"/><path d="M11 2c0 4-1 6-3 8"/><path d="M4 14h8"/></svg>,
  ai:   <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="8" cy="8" r="6"/><path d="M5 8h6M8 5v6"/><circle cx="8" cy="8" r="2"/></svg>,
  user: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="8" cy="5" r="3"/><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6"/></svg>,
}

const navItems = [
  { section:'Overview', links:[{ to:'/client/dashboard', label:'Dashboard', icon:'dash' }] },
  { section:'My Services', links:[
    { to:'/client/appointments', label:'My Appointments', icon:'cal' },
    { to:'/client/nail-studio', label:'Nail Studio', icon:'nail' },
    { to:'/client/hair-studio', label:'Hair Studio', icon:'hair' },
    { to:'/client/ai-advisor', label:'AI Style Advisor', icon:'ai', badge:'NEW' },
  ]},
  { section:'Account', links:[
    { to:'/client/profile', label:'My Profile', icon:'user' },
  ]},
]

export default function ClientSidebar() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() { logout(); navigate('/login') }

  return (
    <aside className="w-[240px] min-h-screen bg-[#1a0a2e] border-r border-[#b040d8]/15 flex flex-col fixed top-0 left-0 z-[100]">
      <div className="px-6 pt-7 pb-6 border-b border-[#b040d8]/15">
        <span className="block font-serif text-[18px] font-semibold tracking-[3px] text-white">ANDREA'S</span>
        <span className="block font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">My Account</span>
      </div>
      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map(({ section, links }) => (
          <div key={section}>
            <p className="text-[9px] font-bold tracking-[2px] text-[#6a4a88] uppercase px-6 pt-3 pb-1.5">{section}</p>
            {links.map(({ to, label, icon, badge }) => {
              const active = pathname === to
              return (
                <Link key={to} to={to}
                  className={`flex items-center gap-2.5 px-6 py-[11px] text-xs font-medium border-l-[3px] transition-all duration-200 no-underline
                    ${active ? 'text-[#f0a800] bg-[#f0a800]/7 border-l-[#f0a800] [&_svg]:opacity-100'
                             : 'text-[#9a7ab8] border-l-transparent hover:text-white hover:bg-[#b040d8]/8 [&_svg]:opacity-60 [&_svg]:hover:opacity-100'}`}>
                  {icons[icon]}
                  <span className="flex-1">{label}</span>
                  {badge && <span className="font-sans text-[8px] font-bold tracking-[1px] bg-[#f0a800] text-[#1a0a2e] px-1.5 py-0.5">{badge}</span>}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
      <div className="px-6 py-5 border-t border-[#b040d8]/15">
        <div className="flex items-center gap-2.5 mb-3.5">
          <div className="w-[34px] h-[34px] rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#f0a800] flex items-center justify-center text-[13px] font-bold text-white shrink-0">
            {user?.avatar || 'M'}
          </div>
          <div>
            <p className="text-xs text-white font-semibold">{user?.name || 'Maria Santos'}</p>
            <span className="text-[10px] text-[#9a7ab8]">Client</span>
          </div>
        </div>
        <button onClick={handleLogout} className="block w-full text-center border border-[#b040d8]/25 text-[#9a7ab8] font-sans text-[10px] font-semibold tracking-[1.5px] uppercase py-[9px] transition-all duration-200 hover:border-[#f0a800] hover:text-[#f0a800] bg-transparent cursor-pointer">
          Sign Out
        </button>
      </div>
    </aside>
  )
}
