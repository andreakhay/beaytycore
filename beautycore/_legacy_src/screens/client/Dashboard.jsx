import { Link } from 'react-router-dom'
import ClientSidebar from '../../components/ClientSidebar'

const upcomingAppts = [
  { service:'Nail Studio', date:'Apr 10, 2026', time:'10:00 AM', status:'Confirmed' },
  { service:'Japanese Head Spa', date:'Apr 15, 2026', time:'2:00 PM', status:'Pending' },
]
const recentHistory = [
  { service:'Nail Studio', date:'Apr 7, 2026', staff:'Andrea', amount:'₱350', status:'Completed' },
  { service:'Hair Design', date:'Mar 22, 2026', staff:'Maria', amount:'₱350', status:'Completed' },
  { service:'Massage Therapy', date:'Mar 10, 2026', staff:'Carla', amount:'₱600', status:'Completed' },
  { service:'Japanese Head Spa', date:'Feb 28, 2026', staff:'Jessa', amount:'₱850', status:'Completed' },
]
const quickActions = [
  { to:'/client/appointments', label:'Book Appointment', sub:'Schedule your next visit' },
  { to:'/client/nail-studio', label:'Nail Studio', sub:'Browse & save nail designs' },
  { to:'/client/hair-studio', label:'Hair Studio', sub:'Explore hair styles' },
  { to:'/client/profile', label:'My Profile', sub:'Update your details' },
]

const badgeCls = { Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]', Pending:'bg-[#f0a800]/15 text-[#f0a800]', Completed:'bg-[#7b2fa0]/25 text-[#d060f0]' }
const Badge = ({ s }) => <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${badgeCls[s]||''}`}>{s}</span>
const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

export default function ClientDashboard() {
  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Welcome back, <span className="text-[#f0a800]">Maria</span></h1>
          <Link to="/client/appointments" className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors">+ Book Appointment</Link>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-7 max-[1024px]:grid-cols-2">
            {[
              { label:'Upcoming', value:'2', sub:'appointments' },
              { label:'Completed', value:'14', sub:'total visits' },
              { label:'Loyalty Points', value:'280', sub:'+ 20 this month', gold:true },
              { label:'Total Spent', value:'₱4.2k', sub:'lifetime' },
            ].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[34px] font-normal leading-none mb-1.5 ${s.gold?'text-[#f0a800]':'text-white'}`}>{s.value}</p>
                <p className="text-[10px] text-[#9a7ab8]">{s.sub}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 mb-6" style={{ gridTemplateColumns:'1.4fr 1fr' }}>
            {/* Upcoming */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center justify-between">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Upcoming Appointments</h2>
                <Link to="/client/appointments" className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 hover:border-[#f0a800] hover:text-[#f0a800] transition-all">View All</Link>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead><tr>{['Service','Date','Time','Status'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
                <tbody>
                  {upcomingAppts.map(a => (
                    <tr key={a.service+a.date} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className={tdCls+' text-white'}>{a.service}</td>
                      <td className={tdCls}>{a.date}</td>
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
                  <Link key={a.to} to={a.to} className="flex items-center gap-3.5 p-3.5 bg-[#b040d8]/6 border border-[#b040d8]/18 transition-all duration-200 hover:bg-[#f0a800]/7 hover:border-[#f0a800]/30 no-underline">
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

          {/* Recent history */}
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Recent Visit History</h2>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['Service','Date','Staff','Amount','Status'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
              <tbody>
                {recentHistory.map(r => (
                  <tr key={r.service+r.date} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className={tdCls+' text-white'}>{r.service}</td>
                    <td className={tdCls}>{r.date}</td>
                    <td className={tdCls}>{r.staff}</td>
                    <td className={tdCls+' text-[#f0a800]'}>{r.amount}</td>
                    <td className={tdCls}><Badge s={r.status} /></td>
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
