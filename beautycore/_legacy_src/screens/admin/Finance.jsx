import { useState } from 'react'
import AdminSidebar from '../../components/AdminSidebar'

const INIT = [
  { id:1,  date:'2026-04-08', desc:'Nail Studio – Maria Santos (Gel Manicure)',    cat:'Service Revenue', type:'income',  amount:350  },
  { id:2,  date:'2026-04-08', desc:'Japanese Head Spa – Jessa Reyes (Classic)',    cat:'Service Revenue', type:'income',  amount:850  },
  { id:3,  date:'2026-04-08', desc:'Hair Design – Carla Dizon (Cut & Blowdry)',    cat:'Service Revenue', type:'income',  amount:350  },
  { id:4,  date:'2026-04-07', desc:'Nail Studio – Luz Garcia (Acrylic Full Set)',  cat:'Service Revenue', type:'income',  amount:650  },
  { id:5,  date:'2026-04-07', desc:'OPI Gel Polish restock (10 pcs)',              cat:'Supplies',        type:'expense', amount:4500 },
  { id:6,  date:'2026-04-06', desc:'Massage Therapy – Ana Lim (Swedish 60 min)',   cat:'Service Revenue', type:'income',  amount:600  },
  { id:7,  date:'2026-04-05', desc:'Electricity bill – April',                     cat:'Utilities',       type:'expense', amount:2800 },
  { id:8,  date:'2026-04-04', desc:'Face & Laser – Rose Tan (Classic Facial)',     cat:'Service Revenue', type:'income',  amount:600  },
  { id:9,  date:'2026-04-03', desc:'Staff salary – Maria (semi-monthly)',          cat:'Salaries',        type:'expense', amount:7500 },
  { id:10, date:'2026-04-02', desc:'Keratin Treatment restock (2 btl)',            cat:'Supplies',        type:'expense', amount:2400 },
  { id:11, date:'2026-04-01', desc:'Rent – April 2026',                            cat:'Rent',            type:'expense', amount:8000 },
  { id:12, date:'2026-04-01', desc:'Hair Design – walk-in (Full Colour)',          cat:'Service Revenue', type:'income',  amount:800  },
  { id:13, date:'2026-04-09', desc:'Nail Studio – walk-in (Gel Pedicure)',         cat:'Service Revenue', type:'income',  amount:400  },
  { id:14, date:'2026-04-09', desc:'Massage Therapy – Tina Cruz (Deep Tissue)',    cat:'Service Revenue', type:'income',  amount:700  },
  { id:15, date:'2026-04-09', desc:'Water bill – April',                           cat:'Utilities',       type:'expense', amount:650  },
]
const CATS = ['Service Revenue','Product Sales','Supplies','Utilities','Salaries','Rent','Other']
const TABS = ['all','income','expense']
const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25 resize-none"
const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"
const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

export default function AdminFinance() {
  const [txns, setTxns] = useState(INIT)
  const [nextId, setNextId] = useState(16)
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [month, setMonth] = useState('')
  const [catF, setCatF] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ desc:'', type:'income', cat:CATS[0], amount:'', date:'' })

  const income   = txns.filter(t=>t.type==='income').reduce((s,t)=>s+t.amount,0)
  const expenses = txns.filter(t=>t.type==='expense').reduce((s,t)=>s+t.amount,0)
  const net      = income - expenses
  const margin   = income > 0 ? Math.round(net/income*100) : 0

  const filtered = txns.filter(t => {
    const matchTab    = tab === 'all' || t.type === tab
    const matchSearch = t.desc.toLowerCase().includes(search.toLowerCase()) || t.cat.toLowerCase().includes(search.toLowerCase())
    const matchMonth  = !month || t.date.startsWith(month)
    const matchCat    = !catF || t.cat === catF
    return matchTab && matchSearch && matchMonth && matchCat
  })

  const services = ['Nail Studio','Hair Design','Face & Laser','Massage Therapy','Japanese Head Spa']
  const svcTotals = services.map(s => ({
    name: s,
    total: txns.filter(t=>t.type==='income'&&t.desc.includes(s.split(' ')[0])).reduce((sum,t)=>sum+t.amount,0)
  })).sort((a,b)=>b.total-a.total)
  const maxSvc = svcTotals[0]?.total || 1

  function addTxn() {
    if (!form.desc || !form.amount || !form.date) return alert('Fill all required fields.')
    setTxns(prev => [{ ...form, id: nextId, amount: parseFloat(form.amount) }, ...prev])
    setNextId(n => n + 1)
    setAddOpen(false)
    setForm({ desc:'', type:'income', cat:CATS[0], amount:'', date:'' })
  }

  function deleteTxn(id) {
    if (!confirm('Delete this transaction?')) return
    setTxns(prev => prev.filter(t => t.id !== id))
  }

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Financial Management</h1>
          <button onClick={() => setAddOpen(true)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors cursor-pointer border-none">+ Record Transaction</button>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-6 max-[1024px]:grid-cols-2">
            {[
              { label:'Total Revenue (Month)', value:'₱'+income.toLocaleString(), color:'text-white' },
              { label:'Total Expenses (Month)', value:'₱'+expenses.toLocaleString(), color:'text-[#eb5757]' },
              { label:'Net Profit (Month)', value:'₱'+net.toLocaleString(), color: net>=0?'text-[#6fcf97]':'text-[#eb5757]' },
              { label:'Transactions (Month)', value: txns.length, color:'text-white' },
            ].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[34px] font-normal leading-none mb-1.5 ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Revenue by Service</h2></div>
              <div className="p-6 flex flex-col gap-3.5">
                {svcTotals.map(s => (
                  <div key={s.name}>
                    <div className="flex justify-between font-sans text-[11px] text-[#e0c8f0] mb-1"><span>{s.name}</span><span className="text-[#f0a800]">₱{s.total.toLocaleString()}</span></div>
                    <div className="bg-[#b040d8]/10 h-1.5 w-full"><div className="progress-bar-fill h-full" style={{ width:`${Math.round(s.total/maxSvc*100)}%` }} /></div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Monthly Summary</h2></div>
              <div className="p-6 flex flex-col gap-3.5">
                {[
                  { label:'Total Income', value:'₱'+income.toLocaleString(), bg:'bg-[#6fcf97]/7 border-[#6fcf97]/15', color:'text-[#6fcf97]' },
                  { label:'Total Expenses', value:'₱'+expenses.toLocaleString(), bg:'bg-[#eb5757]/7 border-[#eb5757]/15', color:'text-[#eb5757]' },
                  { label:'Net Profit', value:'₱'+net.toLocaleString(), bg:'bg-[#f0a800]/7 border-[#f0a800]/20', color:'text-[#f0a800] text-[16px]' },
                  { label:'Profit Margin', value:`${margin}%`, bg:'bg-[#b040d8]/7 border-[#b040d8]/15', color:'text-[#d060f0]' },
                ].map(r => (
                  <div key={r.label} className={`flex justify-between items-center p-3 border ${r.bg}`}>
                    <span className="font-sans text-[11px] text-[#9a7ab8] uppercase tracking-[1px]">{r.label}</span>
                    <span className={`font-semibold ${r.color}`}>{r.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${tab===t?'text-[#f0a800] border-b-[#f0a800]':'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {t.charAt(0).toUpperCase()+t.slice(1)}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-5 flex-wrap">
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search transaction..." className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] min-w-[180px] placeholder:text-white/25" />
            <input type="month" value={month} onChange={e=>setMonth(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800]" />
            <select value={catF} onChange={e=>setCatF(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
              <option value="">All Categories</option>
              {CATS.map(c=><option key={c}>{c}</option>)}
            </select>
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['#','Date','Description','Category','Type','Amount','Actions'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
              <tbody>
                {filtered.length === 0
                  ? <tr><td colSpan={7} className="text-center text-[#6a4a88] py-8">No transactions found.</td></tr>
                  : filtered.map(t => (
                    <tr key={t.id} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className={tdCls+' text-[#6a4a88]'}>#{t.id}</td>
                      <td className={tdCls}>{t.date}</td>
                      <td className={tdCls+' text-white'}>{t.desc}</td>
                      <td className={tdCls}>{t.cat}</td>
                      <td className={tdCls}><span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${t.type==='income'?'bg-[#6fcf97]/15 text-[#6fcf97]':'bg-[#eb5757]/15 text-[#eb5757]'}`}>{t.type==='income'?'Income':'Expense'}</span></td>
                      <td className={tdCls+` font-semibold ${t.type==='income'?'text-[#6fcf97]':'text-[#eb5757]'}`}>{t.type==='income'?'+':'-'}₱{t.amount.toLocaleString()}</td>
                      <td className={tdCls}><button onClick={()=>deleteTxn(t.id)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Delete</button></td>
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
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e=>e.target===e.currentTarget&&setAddOpen(false)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[520px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Record Transaction</h3>
              <button onClick={()=>setAddOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="mb-4"><label className={labelCls}>Description</label><input value={form.desc} onChange={e=>setForm(f=>({...f,desc:e.target.value}))} placeholder="e.g. Nail Studio – Maria Santos" className={inputCls} /></div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Type</label>
                  <select value={form.type} onChange={e=>setForm(f=>({...f,type:e.target.value}))} className={inputCls}>
                    <option value="income">Income</option><option value="expense">Expense</option>
                  </select>
                </div>
                <div><label className={labelCls}>Category</label>
                  <select value={form.cat} onChange={e=>setForm(f=>({...f,cat:e.target.value}))} className={inputCls}>
                    {CATS.map(c=><option key={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Amount (₱)</label><input type="number" value={form.amount} onChange={e=>setForm(f=>({...f,amount:e.target.value}))} min="0" step="0.01" placeholder="0.00" className={inputCls} /></div>
                <div><label className={labelCls}>Date</label><input type="date" value={form.date} onChange={e=>setForm(f=>({...f,date:e.target.value}))} className={inputCls} /></div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={()=>setAddOpen(false)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={addTxn} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
