import StylistSidebar from '../../components/StylistSidebar'

const serviceLog = [
  { client:'Maria Santos',  service:'Nail Studio',       date:'May 7, 2026',  duration:'1h 30m', amount:350,  rating:5 },
  { client:'Lena Gomez',    service:'Hair Design',       date:'May 6, 2026',  duration:'2h 00m', amount:850,  rating:5 },
  { client:'Jessa Reyes',   service:'Nail Studio',       date:'May 5, 2026',  duration:'1h 15m', amount:350,  rating:4 },
  { client:'Ana Dela Cruz', service:'Japanese Head Spa', date:'May 4, 2026',  duration:'1h 00m', amount:600,  rating:5 },
  { client:'Rosa Tan',      service:'Hair Extension',    date:'Apr 30, 2026', duration:'3h 00m', amount:1500, rating:5 },
  { client:'Maria Santos',  service:'Nail Studio',       date:'Apr 28, 2026', duration:'1h 30m', amount:350,  rating:4 },
]

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

export default function StylistServices() {
  const totalEarnings = serviceLog.reduce((s,r) => s+r.amount, 0)
  const avgRating = (serviceLog.reduce((s,r) => s+r.rating, 0) / serviceLog.length).toFixed(1)

  return (
    <div className="flex min-h-screen bg-[#1a0a2e] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Services Done</h1>
        </header>

        <div className="p-8">
          <div className="grid grid-cols-3 gap-5 mb-7">
            {[
              { label:'Services This Month', value: serviceLog.length },
              { label:'Total Earnings',      value: `₱${totalEarnings.toLocaleString()}`, gold:true },
              { label:'Avg. Rating',         value: avgRating },
            ].map(s => (
              <div key={s.label} className="bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px]">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[28px] font-normal leading-none ${s.gold?'text-[#f0a800]':'text-white'}`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Service History</h2>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr>{['Client','Service','Date','Duration','Rating','Amount'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {serviceLog.map((r,i) => (
                  <tr key={i} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className={tdCls+' text-white font-medium'}>{r.client}</td>
                    <td className={tdCls}>{r.service}</td>
                    <td className={tdCls}>{r.date}</td>
                    <td className={tdCls}>{r.duration}</td>
                    <td className={tdCls}><Stars n={r.rating} /></td>
                    <td className={tdCls+' text-[#f0a800]'}>₱{r.amount.toLocaleString()}</td>
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
