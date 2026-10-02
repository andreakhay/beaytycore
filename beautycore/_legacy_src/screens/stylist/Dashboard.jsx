import { Link } from 'react-router-dom'
import StylistSidebar from '../../components/StylistSidebar'
import { useAuth } from '../../context/AuthContext'

const todaySchedule = [
  { client:'Maria Santos',  service:'Nail Studio',       time:'10:00 AM', status:'Confirmed' },
  { client:'Jessa Reyes',   service:'Hair Extension',    time:'1:00 PM',  status:'Confirmed' },
  { client:'Ana Dela Cruz', service:'Japanese Head Spa', time:'3:30 PM',  status:'Pending'   },
]
const recentServices = [
  { client:'Maria Santos',  service:'Nail Studio',  date:'May 7, 2026', amount:'₱350',  rating:5 },
  { client:'Lena Gomez',    service:'Hair Design',  date:'May 6, 2026', amount:'₱850',  rating:5 },
  { client:'Jessa Reyes',   service:'Nail Studio',  date:'May 5, 2026', amount:'₱350',  rating:4 },
  { client:'Ana Dela Cruz', service:'Head Spa',     date:'May 4, 2026', amount:'₱600',  rating:5 },
]
const quickActions = [
  { to:'/stylist/appointments', label:'My Schedule',  sub:"View today's bookings" },
  { to:'/stylist/clients',      label:'My Clients',   sub:'Client history & notes' },
  { to:'/stylist/nail-studio',  label:'Nail Designs', sub:'Browse design catalog' },
  { to:'/stylist/hair-studio',  label:'Hair Styles',  sub:'Explore hair styles' },
]

const badgeCls = {
  Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]',
  Pending:  'bg-[#f0a800]/15 text-[#f0a800]',
  Completed:'bg-[#7b2fa0]/25 text-[#d060f0]',
}
const Badge = ({ s }) => <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${badgeCls[s]||''}`}>{s}</span>

function Stars({ n }) {
  return (
    <span className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <svg key={i} className={`w-2.5 h-2.5 ${i<=n?'text-[#f0a800]':'text-[#3a2050]'}`} viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 1l1.8 3.6L14 5.3l-3 2.9.7 4.1L8 10.4l-3.7 1.9.7-4.1-3-2.9 4.2-.7z"/>
        </svg>
      ))}
    </span>
  )
}

const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

export default function StylistDashboard() {
  const { user } = useAuth()
  const today = new Date().toLocaleDateString('en-PH', { weekday:'long', year:'numeric', month:'long', day:'numeric' })

  return (
    <div className="flex min-h-screen bg-[#1a0a2e] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">

        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">
            Welcome, <span className="text-[#f0a800]">{user?.name || 'Stylist'}</span>
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-[11px] text-[#9a7ab8]">{today}</span>
            <Link to="/stylist/appointments"
              className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors">
              View Schedule
            </Link>
          </div>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-7 max-[1024px]:grid-cols-2">
            {[
              { label:"Today's Bookings", value:'3',   sub:'scheduled today' },
              { label:'This Week',        value:'14',  sub:'total services' },
              { label:'Clients Served',   value:'38',  sub:'this month', gold:true },
              { label:'Avg. Rating',      value:'4.9', sub:'out of 5.0' },
            ].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[34px] font-normal leading-none mb-1.5 ${s.gold?'text-[#f0a800]':'text-white'}`}>{s.value}</p>
                <p className="text-[10px] text-[#9a7ab8]">{s.sub}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 mb-6" style={{ gridTemplateColumns:'1.4fr 1fr' }}>
            {/* Today's schedule */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center justify-between">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Today's Schedule</h2>
                <Link to="/stylist/appointments"
                  className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 hover:border-[#f0a800] hover:text-[#f0a800] transition-all">
                  Full Schedule
                </Link>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead><tr>{['Client','Service','Time','Status'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
                <tbody>
                  {todaySchedule.map(a => (
                    <tr key={a.client+a.time} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className={tdCls+' text-white'}>{a.client}</td>
                      <td className={tdCls}>{a.service}</td>
                      <td className={tdCls}>{a.time}</td>
                      <td className={tdCls}><Badge s={a.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Quick actions */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Quick Actions</h2>
              </div>
              <div className="p-6 flex flex-col gap-3">
                {quickActions.map(a => (
                  <Link key={a.to} to={a.to}
                    className="flex items-center gap-3.5 p-3.5 bg-[#b040d8]/6 border border-[#b040d8]/18 transition-all duration-200 hover:bg-[#f0a800]/7 hover:border-[#f0a800]/30 no-underline">
                    <div className="w-10 h-10 flex items-center justify-center bg-[#b040d8]/12 shrink-0 text-[#f0a800] font-bold text-xs">{a.label.charAt(0)}</div>
                    <div>
                      <p className="text-xs font-semibold text-white mb-0.5">{a.label}</p>
                      <span className="text-[10px] text-[#9a7ab8]">{a.sub}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Recent services */}
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center justify-between">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Recent Services</h2>
              <Link to="/stylist/services"
                className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 hover:border-[#f0a800] hover:text-[#f0a800] transition-all">
                View All
              </Link>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['Client','Service','Date','Rating','Amount'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
              <tbody>
                {recentServices.map((r,i) => (
                  <tr key={i} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className={tdCls+' text-white'}>{r.client}</td>
                    <td className={tdCls}>{r.service}</td>
                    <td className={tdCls}>{r.date}</td>
                    <td className={tdCls}><Stars n={r.rating} /></td>
                    <td className={tdCls+' text-[#f0a800]'}>{r.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
