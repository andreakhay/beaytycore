import { useState } from 'react'
import StylistSidebar from '../../components/StylistSidebar'

const allAppointments = [
  { id:1, client:'Maria Santos',  service:'Nail Studio',       date:'May 9, 2026',  time:'10:00 AM', duration:'1h 30m', status:'Confirmed', notes:'Prefers pastel colors' },
  { id:2, client:'Jessa Reyes',   service:'Hair Extension',    date:'May 9, 2026',  time:'1:00 PM',  duration:'2h 00m', status:'Confirmed', notes:'Tape-in extensions' },
  { id:3, client:'Ana Dela Cruz', service:'Japanese Head Spa', date:'May 9, 2026',  time:'3:30 PM',  duration:'1h 00m', status:'Pending',   notes:'' },
  { id:4, client:'Lena Gomez',    service:'Nail Studio',       date:'May 10, 2026', time:'11:00 AM', duration:'1h 30m', status:'Confirmed', notes:'Gel nails, nude tone' },
  { id:5, client:'Rosa Tan',      service:'Hair Design',       date:'May 10, 2026', time:'2:00 PM',  duration:'2h 30m', status:'Pending',   notes:'Balayage' },
  { id:6, client:'Maria Santos',  service:'Nail Studio',       date:'May 12, 2026', time:'10:00 AM', duration:'1h 30m', status:'Confirmed', notes:'' },
]

const badgeCls = {
  Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]',
  Pending:  'bg-[#f0a800]/15 text-[#f0a800]',
  Completed:'bg-[#7b2fa0]/25 text-[#d060f0]',
  Cancelled:'bg-[#eb5757]/15 text-[#eb5757]',
}
const Badge = ({ s }) => <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${badgeCls[s]||''}`}>{s}</span>

const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"
const filters = ['All','Confirmed','Pending','Completed']

export default function StylistAppointments() {
  const [filter, setFilter] = useState('All')
  const filtered = filter === 'All' ? allAppointments : allAppointments.filter(a => a.status === filter)

  return (
    <div className="flex min-h-screen bg-[#1a0a2e] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">My Schedule</h1>
          <div className="flex gap-2">
            {filters.map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`font-sans text-[9px] font-bold tracking-[1.5px] uppercase px-3.5 py-1.5 border transition-all cursor-pointer
                  ${filter===f ? 'bg-[#f0a800] text-[#1a0a2e] border-[#f0a800]' : 'bg-transparent text-[#9a7ab8] border-[#b040d8]/30 hover:border-[#f0a800] hover:text-[#f0a800]'}`}>
                {f}
              </button>
            ))}
          </div>
        </header>

        <div className="p-8">
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">
                {filter === 'All' ? 'All Appointments' : filter + ' Appointments'}
                <span className="ml-3 font-sans text-[11px] text-[#9a7ab8]">({filtered.length})</span>
              </h2>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr>{['Client','Service','Date','Time','Duration','Status','Notes'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {filtered.map(a => (
                  <tr key={a.id} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className={tdCls+' text-white font-medium'}>{a.client}</td>
                    <td className={tdCls}>{a.service}</td>
                    <td className={tdCls}>{a.date}</td>
                    <td className={tdCls}>{a.time}</td>
                    <td className={tdCls}>{a.duration}</td>
                    <td className={tdCls}><Badge s={a.status} /></td>
                    <td className={tdCls+' text-[#9a7ab8] italic'}>{a.notes || '—'}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={7} className="px-3.5 py-8 text-center text-[#9a7ab8] text-xs">No appointments found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
