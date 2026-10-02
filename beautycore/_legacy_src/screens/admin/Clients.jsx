import { useState } from 'react'
import AdminSidebar from '../../components/AdminSidebar'

const INIT = [
  { id:1, first:'Maria',  last:'Santos', email:'maria@email.com',  phone:'+63 912 111 1111', service:'Nail Studio',       visits:14, lastVisit:'2026-04-07', birthday:'1995-03-12', notes:'Prefers gel nails' },
  { id:2, first:'Jessa',  last:'Reyes',  email:'jessa@email.com',  phone:'+63 912 222 2222', service:'Japanese Head Spa', visits:8,  lastVisit:'2026-04-08', birthday:'1998-07-22', notes:'Sensitive scalp' },
  { id:3, first:'Carla',  last:'Dizon',  email:'carla@email.com',  phone:'+63 912 333 3333', service:'Hair Design',       visits:11, lastVisit:'2026-04-08', birthday:'1993-11-05', notes:'' },
  { id:4, first:'Ana',    last:'Lim',    email:'ana@email.com',    phone:'+63 912 444 4444', service:'Massage Therapy',   visits:6,  lastVisit:'2026-04-08', birthday:'1990-01-30', notes:'Deep tissue preferred' },
  { id:5, first:'Rose',   last:'Tan',    email:'rose@email.com',   phone:'+63 912 555 5555', service:'Face & Laser',      visits:3,  lastVisit:'2026-03-20', birthday:'2000-06-15', notes:'' },
  { id:6, first:'Luz',    last:'Garcia', email:'luz@email.com',    phone:'+63 912 666 6666', service:'Nail Studio',       visits:20, lastVisit:'2026-04-07', birthday:'1988-09-08', notes:'VIP client' },
  { id:7, first:'Tina',   last:'Cruz',   email:'tina@email.com',   phone:'+63 912 777 7777', service:'Hair Design',       visits:5,  lastVisit:'2026-03-15', birthday:'1997-04-20', notes:'' },
]
const SERVICES = ['Japanese Head Spa','Hair Design','Face & Laser','Nail Studio','Massage Therapy']
const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25 resize-none"
const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"
const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

export default function AdminClients() {
  const [clients, setClients] = useState(INIT)
  const [nextId, setNextId] = useState(8)
  const [search, setSearch] = useState('')
  const [svcFilter, setSvcFilter] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [viewData, setViewData] = useState(null)
  const [form, setForm] = useState({ first:'', last:'', email:'', phone:'', service:SERVICES[0], birthday:'', notes:'' })

  const filtered = clients.filter(c => {
    const matchSearch = `${c.first} ${c.last} ${c.email} ${c.phone}`.toLowerCase().includes(search.toLowerCase())
    const matchSvc = !svcFilter || c.service === svcFilter
    return matchSearch && matchSvc
  })

  function addClient() {
    if (!form.first || !form.last) return alert('Name is required.')
    setClients(prev => [...prev, { ...form, id: nextId, visits: 0, lastVisit: '—' }])
    setNextId(n => n + 1)
    setAddOpen(false)
    setForm({ first:'', last:'', email:'', phone:'', service:SERVICES[0], birthday:'', notes:'' })
  }

  function deleteClient(id) {
    if (!confirm('Delete this client?')) return
    setClients(prev => prev.filter(c => c.id !== id))
  }

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Client Management (CRM)</h1>
          <button onClick={() => setAddOpen(true)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors cursor-pointer border-none">+ Add Client</button>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-5 mb-6">
            {[{ label:'Total Clients', value:'247', change:'+ 12 this month', up:true },
              { label:'Returning Clients', value:'189', change:'76% retention rate', up:false },
              { label:'New This Month', value:'12', change:'+ 4 vs last month', up:true }].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className="font-serif text-[34px] font-normal text-white leading-none mb-1.5">{s.value}</p>
                <p className={`text-[10px] ${s.up ? 'text-[#6fcf97]' : 'text-[#9a7ab8]'}`}>{s.change}</p>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-5 flex-wrap">
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name, email or phone..." className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] min-w-[220px] placeholder:text-white/25" />
            <select value={svcFilter} onChange={e => setSvcFilter(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
              <option value="">All Services</option>
              {SERVICES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['#','Name','Email','Phone','Preferred Service','Total Visits','Last Visit','Actions'].map(h => <th key={h} className={thCls}>{h}</th>)}</tr></thead>
              <tbody>
                {filtered.length === 0
                  ? <tr><td colSpan={8} className="text-center text-[#6a4a88] py-8">No clients found.</td></tr>
                  : filtered.map(c => (
                    <tr key={c.id} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className={tdCls + ' text-[#6a4a88]'}>#{c.id}</td>
                      <td className={tdCls + ' font-semibold text-white'}>{c.first} {c.last}</td>
                      <td className={tdCls}>{c.email}</td>
                      <td className={tdCls}>{c.phone}</td>
                      <td className={tdCls}>{c.service}</td>
                      <td className={tdCls + ' text-center'}>{c.visits}</td>
                      <td className={tdCls}>{c.lastVisit}</td>
                      <td className={tdCls}>
                        <div className="flex gap-1.5">
                          <button onClick={() => setViewData(c)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">View</button>
                          <button onClick={() => deleteClient(c.id)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Delete</button>
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

      {/* Add Modal */}
      {addOpen && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e => e.target === e.currentTarget && setAddOpen(false)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[520px] max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Add New Client</h3>
              <button onClick={() => setAddOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>First Name</label><input value={form.first} onChange={e=>setForm(f=>({...f,first:e.target.value}))} placeholder="Maria" className={inputCls} /></div>
                <div><label className={labelCls}>Last Name</label><input value={form.last} onChange={e=>setForm(f=>({...f,last:e.target.value}))} placeholder="Santos" className={inputCls} /></div>
              </div>
              <div className="mb-4"><label className={labelCls}>Email</label><input type="email" value={form.email} onChange={e=>setForm(f=>({...f,email:e.target.value}))} placeholder="client@email.com" className={inputCls} /></div>
              <div className="mb-4"><label className={labelCls}>Phone</label><input value={form.phone} onChange={e=>setForm(f=>({...f,phone:e.target.value}))} placeholder="+63 912 345 6789" className={inputCls} /></div>
              <div className="mb-4"><label className={labelCls}>Preferred Service</label>
                <select value={form.service} onChange={e=>setForm(f=>({...f,service:e.target.value}))} className={inputCls}>
                  {SERVICES.map(s=><option key={s}>{s}</option>)}
                </select>
              </div>
              <div className="mb-4"><label className={labelCls}>Birthday</label><input type="date" value={form.birthday} onChange={e=>setForm(f=>({...f,birthday:e.target.value}))} className={inputCls} /></div>
              <div><label className={labelCls}>Notes / Preferences</label><textarea value={form.notes} onChange={e=>setForm(f=>({...f,notes:e.target.value}))} rows={3} placeholder="Allergies, preferences..." className={inputCls} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={() => setAddOpen(false)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={addClient} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Save Client</button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {viewData && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e => e.target === e.currentTarget && setViewData(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[600px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">{viewData.first} {viewData.last}</h3>
              <button onClick={() => setViewData(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6 grid grid-cols-2 gap-4 mb-5">
              {[['Email',viewData.email],['Phone',viewData.phone],['Preferred Service',viewData.service],['Birthday',viewData.birthday||'—']].map(([k,v])=>(
                <div key={k}><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">{k}</p><p className="text-white text-xs">{v}</p></div>
              ))}
              <div><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Total Visits</p><p className="font-serif text-[20px] text-[#f0a800]">{viewData.visits}</p></div>
              <div><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Last Visit</p><p className="text-white text-xs">{viewData.lastVisit}</p></div>
            </div>
            {viewData.notes && <div className="mx-6 mb-6 bg-[#b040d8]/7 border border-[#b040d8]/20 p-3.5"><p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1.5">Notes</p><p className="text-[#e0c8f0] text-xs leading-[1.7]">{viewData.notes}</p></div>}
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex justify-end">
              <button onClick={() => setViewData(null)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
