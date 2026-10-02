import { useState } from 'react'
import StylistSidebar from '../../components/StylistSidebar'

const clients = [
  { name:'Maria Santos',  visits:12, lastVisit:'May 7, 2026',  preferred:'Nail Studio',    spend:'₱4,200', notes:'Prefers pastel colors, gel nails' },
  { name:'Jessa Reyes',   visits:8,  lastVisit:'May 5, 2026',  preferred:'Hair Extension', spend:'₱6,800', notes:'Tape-in extensions, dark brown' },
  { name:'Ana Dela Cruz', visits:5,  lastVisit:'May 4, 2026',  preferred:'Head Spa',       spend:'₱3,000', notes:'Sensitive scalp' },
  { name:'Lena Gomez',    visits:9,  lastVisit:'May 6, 2026',  preferred:'Nail Studio',    spend:'₱3,150', notes:'Gel nails, nude tones' },
  { name:'Rosa Tan',      visits:3,  lastVisit:'Apr 28, 2026', preferred:'Hair Design',    spend:'₱4,500', notes:'Balayage, medium length' },
]

const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

export default function StylistClients() {
  const [search, setSearch] = useState('')
  const filtered = clients.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
  const totalVisits = clients.reduce((s,c) => s+c.visits, 0)
  const avgVisits = (totalVisits / clients.length).toFixed(1)

  return (
    <div className="flex min-h-screen bg-[#1a0a2e] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">My Clients</h1>
          <input type="text" placeholder="Search clients…" value={search} onChange={e => setSearch(e.target.value)}
            className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white text-[11px] px-3.5 py-2 outline-none focus:border-[#f0a800] placeholder:text-white/25 w-44 transition-colors" />
        </header>

        <div className="p-8">
          {/* Summary */}
          <div className="grid grid-cols-3 gap-5 mb-7">
            {[
              { label:'Total Clients',  value: clients.length },
              { label:'Avg. Visits',    value: avgVisits },
              { label:'Most Requested', value: 'Nail Studio', gold:true },
            ].map(s => (
              <div key={s.label} className="bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px]">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[28px] font-normal leading-none ${s.gold?'text-[#f0a800]':'text-white'}`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Client List</h2>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr>{['Client','Total Visits','Total Spend','Last Visit','Preferred Service','Notes'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.name} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className={tdCls+' text-white font-medium'}>{c.name}</td>
                    <td className={tdCls+' text-[#f0a800]'}>{c.visits}</td>
                    <td className={tdCls+' text-[#f0a800]'}>{c.spend}</td>
                    <td className={tdCls}>{c.lastVisit}</td>
                    <td className={tdCls}>{c.preferred}</td>
                    <td className={tdCls+' text-[#9a7ab8] italic'}>{c.notes}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={6} className="px-3.5 py-8 text-center text-[#9a7ab8] text-xs">No clients found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
