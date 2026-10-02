import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const icons = {
  dash: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="1" width="6" height="6" rx="0.5"/><rect x="9" y="1" width="6" height="6" rx="0.5"/><rect x="1" y="9" width="6" height="6" rx="0.5"/><rect x="9" y="9" width="6" height="6" rx="0.5"/></svg>,
  cal:  <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="2" width="14" height="13" rx="1"/><line x1="5" y1="1" x2="5" y2="4"/><line x1="11" y1="1" x2="11" y2="4"/><line x1="1" y1="6" x2="15" y2="6"/></svg>,
  user: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="8" cy="5" r="3"/><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6"/></svg>,
  box:  <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="4" width="14" height="10" rx="1"/><path d="M5 4V3a3 3 0 016 0v1"/></svg>,
  card: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="3" width="14" height="10" rx="1"/><line x1="1" y1="7" x2="15" y2="7"/><line x1="5" y1="11" x2="7" y2="11"/></svg>,
  trend:<svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="1,12 5,7 9,9 15,3"/><polyline points="11,3 15,3 15,7"/></svg>,
  lock: <svg className="w-[15px] h-[15px] shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="7" width="10" height="8" rx="1"/><path d="M5 7V5a3 3 0 016 0v2"/><circle cx="8" cy="11" r="1"/></svg>,
}

const navItems = [
  { section:'Overview', links:[{ to:'/admin/dashboard', label:'Dashboard', icon:'dash' }] },
  { section:'Management', links:[
    { to:'/admin/appointments', label:'Appointments', icon:'cal' },
    { to:'/admin/clients', label:'Clients (CRM)', icon:'user' },
    { to:'/admin/inventory', label:'Inventory', icon:'box' },
    { to:'/admin/finance', label:'Financial', icon:'card' },
  ]},
  { section:'Analytics', links:[
    { to:'/admin/market-trends', label:'Market Trends', icon:'trend' },
  ]},
  { section:'System', links:[
    { to:'/admin/security', label:'Security & Access', icon:'lock' },
  ]},
]

export default function AdminSidebar() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() { logout(); navigate('/login') }

  return (
    <aside className="w-[240px] min-h-screen bg-[#1a0a2e] border-r border-[#b040d8]/15 flex flex-col fixed top-0 left-0 z-[100]">
      <div className="px-6 pt-7 pb-6 border-b border-[#b040d8]/15">
        <span className="block font-serif text-[18px] font-semibold tracking-[3px] text-white">ANDREA'S</span>
        <span className="block font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">Admin Panel</span>
      </div>
      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map(({ section, links }) => (
          <div key={section}>
            <p className="text-[9px] font-bold tracking-[2px] text-[#6a4a88] uppercase px-6 pt-3 pb-1.5">{section}</p>
            {links.map(({ to, label, icon }) => {
              const active = pathname === to
              return (
                <Link key={to} to={to}
                  className={`flex items-center gap-2.5 px-6 py-[11px] text-xs font-medium border-l-[3px] transition-all duration-200 no-underline
                    ${active ? 'text-[#f0a800] bg-[#f0a800]/7 border-l-[#f0a800] [&_svg]:opacity-100'
                             : 'text-[#9a7ab8] border-l-transparent hover:text-white hover:bg-[#b040d8]/8 [&_svg]:opacity-60 [&_svg]:hover:opacity-100'}`}>
                  {icons[icon]}{label}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
      <div className="px-6 py-5 border-t border-[#b040d8]/15">
        <div className="flex items-center gap-2.5 mb-3.5">
          <div className="w-[34px] h-[34px] rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#f0a800] flex items-center justify-center text-[13px] font-bold text-white shrink-0">
            {user?.avatar || 'A'}
          </div>
          <div>
            <p className="text-xs text-white font-semibold">{user?.name || 'Andrea'}</p>
            <span className="text-[10px] text-[#9a7ab8]">Administrator</span>
          </div>
        </div>
        <button onClick={handleLogout} className="block w-full text-center border border-[#b040d8]/25 text-[#9a7ab8] font-sans text-[10px] font-semibold tracking-[1.5px] uppercase py-[9px] transition-all duration-200 hover:border-[#f0a800] hover:text-[#f0a800] bg-transparent cursor-pointer">
          Sign Out
        </button>
      </div>
    </aside>
  )
}
