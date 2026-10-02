import { useState } from 'react'
import ClientSidebar from '../../components/ClientSidebar'

const INIT = [
  { id:1, service:'Nail Studio',       date:'2026-04-10', time:'10:00 AM', status:'Confirmed', notes:'',              staff:'Andrea' },
  { id:2, service:'Japanese Head Spa', date:'2026-04-15', time:'2:00 PM',  status:'Pending',   notes:'Sensitive scalp', staff:'Jessa' },
  { id:3, service:'Hair Design',       date:'2026-03-22', time:'11:00 AM', status:'Completed', notes:'',              staff:'Maria' },
  { id:4, service:'Massage Therapy',   date:'2026-03-10', time:'3:00 PM',  status:'Completed', notes:'Deep tissue',   staff:'Carla' },
  { id:5, service:'Japanese Head Spa', date:'2026-02-28', time:'1:00 PM',  status:'Completed', notes:'',              staff:'Jessa' },
  { id:6, service:'Face & Laser',      date:'2026-02-10', time:'2:00 PM',  status:'Cancelled', notes:'',              staff:'Andrea' },
]
const SERVICES = ['Japanese Head Spa','Hair Design','Face & Laser','Nail Studio','Massage Therapy']
const TIMES    = ['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM','3:00 PM','4:00 PM','5:00 PM']
const TABS     = ['upcoming','completed','cancelled','all']
const UPCOMING = ['Confirmed','Pending']

const badgeCls = { Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]', Pending:'bg-[#f0a800]/15 text-[#f0a800]', Completed:'bg-[#7b2fa0]/25 text-[#d060f0]', Cancelled:'bg-[#eb5757]/15 text-[#eb5757]' }
const Badge = ({ s }) => <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${badgeCls[s]||''}`}>{s}</span>

const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25 resize-none"
const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"

const SVC_ABBR = { 'Nail Studio':'NS', 'Hair Design':'HD', 'Japanese Head Spa':'JH', 'Massage Therapy':'MT', 'Face & Laser':'FL' }

export default function ClientAppointments() {
  const [appts, setAppts] = useState(INIT)
  const [nextId, setNextId] = useState(7)
  const [tab, setTab] = useState('upcoming')
  const [bookOpen, setBookOpen] = useState(false)
  const [cancelTarget, setCancelTarget] = useState(null)
  const [form, setForm] = useState({ service:SERVICES[0], date:'', time:TIMES[0], notes:'' })

  const filtered = appts.filter(a => {
    if (tab === 'upcoming') return UPCOMING.includes(a.status)
    if (tab === 'all') return true
    return a.status.toLowerCase() === tab
  })

  function bookAppt() {
    if (!form.date) return alert('Please select a date.')
    setAppts(prev => [{ ...form, id: nextId, status:'Pending', staff:'TBD' }, ...prev])
    setNextId(n => n + 1)
    setBookOpen(false)
    setForm({ service:SERVICES[0], date:'', time:TIMES[0], notes:'' })
  }

  function confirmCancel() {
    setAppts(prev => prev.map(a => a.id === cancelTarget ? { ...a, status:'Cancelled' } : a))
    setCancelTarget(null)
  }

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">My Appointments</h1>
          <button onClick={() => setBookOpen(true)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors cursor-pointer border-none">+ Book New</button>
        </header>

        <div className="p-8 flex-1">
          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${tab===t?'text-[#f0a800] border-b-[#f0a800]':'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {t.charAt(0).toUpperCase()+t.slice(1)}
              </button>
            ))}
          </div>

          {filtered.length === 0
            ? <div className="text-center py-16 text-[#6a4a88] text-[13px]">No appointments found.</div>
            : filtered.map(a => (
              <div key={a.id} className="flex justify-between items-start bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-5 mb-3 transition-all duration-200 hover:border-[#f0a800]/30 max-[768px]:flex-col max-[768px]:gap-4">
                <div className="flex gap-4 items-start">
                  <div className="w-11 h-11 flex items-center justify-center bg-[#b040d8]/12 border border-[#b040d8]/20 shrink-0 font-sans text-[11px] font-bold text-[#f0a800]">{SVC_ABBR[a.service]||a.service.charAt(0)}</div>
                  <div>
                    <p className="font-serif text-[18px] font-normal text-white mb-1.5">{a.service}</p>
                    <p className="font-sans text-[11px] text-[#9a7ab8] mb-[3px]"><span className="font-bold tracking-[1.5px] uppercase text-[9px] mr-1.5 min-w-[36px] inline-block">Date</span>{a.date}</p>
                    <p className="font-sans text-[11px] text-[#9a7ab8] mb-[3px]"><span className="font-bold tracking-[1.5px] uppercase text-[9px] mr-1.5 min-w-[36px] inline-block">Time</span>{a.time}</p>
                    <p className="font-sans text-[11px] text-[#9a7ab8] mb-[3px]"><span className="font-bold tracking-[1.5px] uppercase text-[9px] mr-1.5 min-w-[36px] inline-block">Staff</span>{a.staff}</p>
                    {a.notes && <p className="font-sans text-[11px] text-[#c8a8e0] italic mt-1.5">"{a.notes}"</p>}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-3 shrink-0">
                  <Badge s={a.status} />
                  <div className="flex gap-2 flex-wrap justify-end">
                    {UPCOMING.includes(a.status) && <button onClick={() => setCancelTarget(a.id)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Cancel</button>}
                    {a.status === 'Completed' && <button onClick={() => { setForm(f=>({...f,service:a.service})); setBookOpen(true) }} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Rebook</button>}
                  </div>
                </div>
              </div>
            ))
          }
        </div>
      </div>

      {/* Book Modal */}
      {bookOpen && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e=>e.target===e.currentTarget&&setBookOpen(false)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[540px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Book an Appointment</h3>
              <button onClick={()=>setBookOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="mb-4"><label className={labelCls}>Service</label>
                <select value={form.service} onChange={e=>setForm(f=>({...f,service:e.target.value}))} className={inputCls}>
                  {SERVICES.map(s=><option key={s}>{s}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Date</label><input type="date" value={form.date} onChange={e=>setForm(f=>({...f,date:e.target.value}))} className={inputCls} /></div>
                <div><label className={labelCls}>Time</label>
                  <select value={form.time} onChange={e=>setForm(f=>({...f,time:e.target.value}))} className={inputCls}>
                    {TIMES.map(t=><option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div><label className={labelCls}>Special Requests</label><textarea value={form.notes} onChange={e=>setForm(f=>({...f,notes:e.target.value}))} rows={3} placeholder="Any notes for your therapist..." className={inputCls} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={()=>setBookOpen(false)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={bookAppt} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Confirm Booking</button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Confirm Modal */}
      {cancelTarget && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e=>e.target===e.currentTarget&&setCancelTarget(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[380px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Cancel Appointment</h3>
              <button onClick={()=>setCancelTarget(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6"><p className="text-[#e0c8f0] text-[13px] leading-[1.7]">Are you sure you want to cancel this appointment? This action cannot be undone.</p></div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={()=>setCancelTarget(null)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Keep It</button>
              <button onClick={confirmCancel} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Yes, Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
