import { useState } from 'react'
import AdminSidebar from '../../components/AdminSidebar'

const INIT = [
  { id:1, client:'Maria Santos',  phone:'+63 912 111 1111', service:'Nail Studio',       date:'2026-04-08', time:'9:00 AM',  staff:'Andrea', status:'Confirmed', notes:'' },
  { id:2, client:'Jessa Reyes',   phone:'+63 912 222 2222', service:'Japanese Head Spa', date:'2026-04-08', time:'10:00 AM', staff:'Maria',  status:'Confirmed', notes:'Sensitive scalp' },
  { id:3, client:'Carla Dizon',   phone:'+63 912 333 3333', service:'Hair Design',       date:'2026-04-08', time:'11:30 AM', staff:'Jessa',  status:'Pending',   notes:'' },
  { id:4, client:'Ana Lim',       phone:'+63 912 444 4444', service:'Massage Therapy',   date:'2026-04-08', time:'1:00 PM',  staff:'Carla',  status:'Confirmed', notes:'Deep tissue' },
  { id:5, client:'Rose Tan',      phone:'+63 912 555 5555', service:'Face & Laser',      date:'2026-04-09', time:'3:00 PM',  staff:'Andrea', status:'Pending',   notes:'' },
  { id:6, client:'Luz Garcia',    phone:'+63 912 666 6666', service:'Nail Studio',       date:'2026-04-07', time:'2:00 PM',  staff:'Maria',  status:'Completed', notes:'' },
  { id:7, client:'Tina Cruz',     phone:'+63 912 777 7777', service:'Hair Design',       date:'2026-04-06', time:'11:00 AM', staff:'Jessa',  status:'Cancelled', notes:'Client no-show' },
]
const SERVICES = ['Japanese Head Spa','Hair Design','Face & Laser','Nail Studio','Massage Therapy']
const TIMES    = ['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM','3:00 PM','4:00 PM','5:00 PM']
const STAFF    = ['Andrea','Maria','Jessa','Carla']
const TABS     = ['all','pending','confirmed','completed','cancelled']

const badgeCls = { Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]', Pending:'bg-[#f0a800]/15 text-[#f0a800]', Completed:'bg-[#7b2fa0]/25 text-[#d060f0]', Cancelled:'bg-[#eb5757]/15 text-[#eb5757]' }
const Badge = ({ s }) => <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${badgeCls[s]||''}`}>{s}</span>

const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25 resize-none"
const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"

export default function AdminAppointments() {
  const [appts, setAppts] = useState(INIT)
  const [nextId, setNextId] = useState(8)
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [dateF, setDateF] = useState('')
  const [statusF, setStatusF] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [viewData, setViewData] = useState(null)
  const [form, setForm] = useState({ client:'', phone:'', service:SERVICES[0], date:'', time:TIMES[0], staff:STAFF[0], notes:'' })

  const filtered = appts.filter(a => {
    const matchTab = tab === 'all' || a.status.toLowerCase() === tab
    const matchSearch = a.client.toLowerCase().includes(search.toLowerCase()) || a.service.toLowerCase().includes(search.toLowerCase())
    const matchDate = !dateF || a.date === dateF
    const matchStatus = !statusF || a.status === statusF
    return matchTab && matchSearch && matchDate && matchStatus
  })

  function updateStatus(id, status) { setAppts(prev => prev.map(a => a.id === id ? { ...a, status } : a)) }

  function addAppt() {
    if (!form.client || !form.date) return alert('Fill required fields.')
    setAppts(prev => [...prev, { ...form, id: nextId, status: 'Pending' }])
    setNextId(n => n + 1)
    setAddOpen(false)
    setForm({ client:'', phone:'', service:SERVICES[0], date:'', time:TIMES[0], staff:STAFF[0], notes:'' })
  }

  const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
  const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Appointments</h1>
          <button onClick={() => setAddOpen(true)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors cursor-pointer border-none">+ New Appointment</button>
        </header>

        <div className="p-8 flex-1">
          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${tab === t ? 'text-[#f0a800] border-b-[#f0a800]' : 'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-5 flex-wrap">
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search client or service..." className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] min-w-[180px] placeholder:text-white/25" />
            <input type="date" value={dateF} onChange={e => setDateF(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800]" />
            <select value={statusF} onChange={e => setStatusF(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
              <option value="">All Statuses</option>
              {['Confirmed','Pending','Completed','Cancelled'].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead><tr>{['#','Client','Service','Date','Time','Staff','Status','Actions'].map(h => <th key={h} className={thCls}>{h}</th>)}</tr></thead>
                <tbody>
                  {filtered.length === 0
                    ? <tr><td colSpan={8} className="text-center text-[#6a4a88] py-8">No appointments found.</td></tr>
                    : filtered.map(a => (
                      <tr key={a.id} className="hover:bg-[#b040d8]/5 transition-colors">
                        <td className={tdCls + ' text-[#6a4a88]'}>#{a.id}</td>
                        <td className={tdCls}>{a.client}</td>
                        <td className={tdCls}>{a.service}</td>
                        <td className={tdCls}>{a.date}</td>
                        <td className={tdCls}>{a.time}</td>
                        <td className={tdCls}>{a.staff}</td>
                        <td className={tdCls}><Badge s={a.status} /></td>
                        <td className={tdCls}>
                          <div className="flex gap-1.5 flex-wrap">
                            <button onClick={() => setViewData(a)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">View</button>
                            {a.status === 'Pending' && <button onClick={() => updateStatus(a.id,'Confirmed')} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Confirm</button>}
                            {a.status === 'Confirmed' && <button onClick={() => updateStatus(a.id,'Completed')} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Complete</button>}
                            {!['Cancelled','Completed'].includes(a.status) && <button onClick={() => updateStatus(a.id,'Cancelled')} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Cancel</button>}
                          </div>
                        </td>
                      </tr>
                    ))
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Add Modal */}
      {addOpen && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e => e.target === e.currentTarget && setAddOpen(false)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[520px] max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">New Appointment</h3>
              <button onClick={() => setAddOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Client Name</label><input value={form.client} onChange={e => setForm(f=>({...f,client:e.target.value}))} placeholder="Full name" className={inputCls} /></div>
                <div><label className={labelCls}>Phone</label><input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} placeholder="+63 912 345 6789" className={inputCls} /></div>
              </div>
              <div className="mb-4"><label className={labelCls}>Service</label>
                <select value={form.service} onChange={e => setForm(f=>({...f,service:e.target.value}))} className={inputCls}>
                  {SERVICES.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Date</label><input type="date" value={form.date} onChange={e => setForm(f=>({...f,date:e.target.value}))} className={inputCls} /></div>
                <div><label className={labelCls}>Time</label>
                  <select value={form.time} onChange={e => setForm(f=>({...f,time:e.target.value}))} className={inputCls}>
                    {TIMES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="mb-4"><label className={labelCls}>Assigned Staff</label>
                <select value={form.staff} onChange={e => setForm(f=>({...f,staff:e.target.value}))} className={inputCls}>
                  {STAFF.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div><label className={labelCls}>Notes</label><textarea value={form.notes} onChange={e => setForm(f=>({...f,notes:e.target.value}))} rows={3} placeholder="Special requests..." className={inputCls} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={() => setAddOpen(false)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={addAppt} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Save Appointment</button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {viewData && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e => e.target === e.currentTarget && setViewData(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[520px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Appointment Details</h3>
              <button onClick={() => setViewData(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6 grid grid-cols-2 gap-4">
              {[['Client',viewData.client],['Phone',viewData.phone],['Service',viewData.service],['Staff',viewData.staff],['Date',viewData.date],['Time',viewData.time]].map(([k,v]) => (
                <div key={k}><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">{k}</p><p className="text-white text-[13px]">{v}</p></div>
              ))}
              <div className="col-span-2"><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Status</p><Badge s={viewData.status} /></div>
              {viewData.notes && <div className="col-span-2"><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Notes</p><p className="text-[#e0c8f0] text-xs">{viewData.notes}</p></div>}
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex justify-end">
              <button onClick={() => setViewData(null)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
