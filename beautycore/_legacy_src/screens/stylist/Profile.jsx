import { useAuth } from '../../context/AuthContext'
import StylistSidebar from '../../components/StylistSidebar'

const specialties = ['Nail Art', 'Hair Extensions', 'Japanese Head Spa', 'Hair Coloring']

const recentActivity = [
  { action:'Completed Nail Studio',       client:'Maria Santos',  time:'2h ago'  },
  { action:'Completed Hair Design',       client:'Lena Gomez',    time:'1d ago'  },
  { action:'Completed Nail Studio',       client:'Jessa Reyes',   time:'2d ago'  },
  { action:'Completed Japanese Head Spa', client:'Ana Dela Cruz', time:'3d ago'  },
]

const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"

export default function StylistProfile() {
  const { user } = useAuth()

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">My Profile</h1>
        </header>

        <div className="p-8">
          <div className="grid gap-6" style={{ gridTemplateColumns:'1fr 1.6fr' }}>

            {/* Left column */}
            <div className="flex flex-col gap-5">

              {/* Profile card */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 p-8 flex items-center gap-6">
                <div className="w-[72px] h-[72px] rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#f0a800] flex items-center justify-center text-[28px] font-bold text-white shrink-0">
                  {user?.avatar || 'S'}
                </div>
                <div>
                  <p className="font-serif text-[22px] text-white">{user?.name || 'Lara Cruz'}</p>
                  <p className="text-[#9a7ab8] text-xs mt-1">{user?.email || 'lara@andreas.com'}</p>
                  <span className="inline-block mt-2 font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#7b2fa0]/25 text-[#d060f0] px-2.5 py-[3px]">Stylist</span>
                </div>
              </div>

              {/* Details */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 p-6">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px] mb-5">Profile Details</h2>
                <div className="grid grid-cols-2 gap-5">
                  {[
                    { label:'Full Name',   value: user?.name || 'Lara Cruz' },
                    { label:'Email',       value: user?.email || 'lara@andreas.com' },
                    { label:'Role',        value: 'Stylist' },
                    { label:'Employee ID', value: 'STY-001' },
                    { label:'Joined',      value: 'January 2025' },
                    { label:'Status',      value: 'Active' },
                  ].map(f => (
                    <div key={f.label}>
                      <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-1.5">{f.label}</p>
                      <p className="text-white text-xs">{f.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Specialties */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 p-6">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px] mb-5">Specialties</h2>
                <div className="flex flex-wrap gap-2">
                  {specialties.map(s => (
                    <span key={s} className="font-sans text-[10px] font-semibold tracking-[1px] bg-[#b040d8]/15 text-[#c8a8e0] border border-[#b040d8]/25 px-3 py-1.5">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Right column */}
            <div className="flex flex-col gap-5">

              {/* Performance stats */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 p-6">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px] mb-5">Performance This Month</h2>
                <div className="grid grid-cols-3 gap-5">
                  {[
                    { label:'Services',    value:'38',  sub:'completed' },
                    { label:'Avg. Rating', value:'4.9', sub:'out of 5.0', gold:true },
                    { label:'Earnings',    value:'₱4k', sub:'this month' },
                  ].map(s => (
                    <div key={s.label} className="relative bg-[#b040d8]/6 border border-[#b040d8]/15 px-5 py-[18px] overflow-hidden stat-card-accent">
                      <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2">{s.label}</p>
                      <p className={`font-serif text-[28px] font-normal leading-none mb-1 ${s.gold?'text-[#f0a800]':'text-white'}`}>{s.value}</p>
                      <p className="text-[10px] text-[#9a7ab8]">{s.sub}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent activity */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                  <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Recent Activity</h2>
                </div>
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr>{['Action','Client','Time'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {recentActivity.map((a,i) => (
                      <tr key={i} className="hover:bg-[#b040d8]/5 transition-colors">
                        <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{a.action}</td>
                        <td className="px-3.5 py-3 text-white border-b border-[#b040d8]/7 font-medium">{a.client}</td>
                        <td className="px-3.5 py-3 text-[#9a7ab8] border-b border-[#b040d8]/7">{a.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
