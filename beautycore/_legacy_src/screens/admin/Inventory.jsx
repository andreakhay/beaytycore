import { useState } from 'react'
import AdminSidebar from '../../components/AdminSidebar'

const INIT = [
  { id:1,  name:'OPI Gel Polish – Nude',       cat:'Nail',    stock:3,  min:10, price:450,  unit:'pcs',  supplier:'OPI Philippines' },
  { id:2,  name:'OPI Gel Polish – Red',         cat:'Nail',    stock:12, min:10, price:450,  unit:'pcs',  supplier:'OPI Philippines' },
  { id:3,  name:'Nail Primer',                  cat:'Nail',    stock:2,  min:6,  price:280,  unit:'pcs',  supplier:'Nail Supply Co.' },
  { id:4,  name:'Acrylic Powder – Clear',       cat:'Nail',    stock:8,  min:5,  price:350,  unit:'pcs',  supplier:'Nail Supply Co.' },
  { id:5,  name:'Keratin Treatment 500ml',      cat:'Hair',    stock:1,  min:5,  price:1200, unit:'btl',  supplier:'Wella PH' },
  { id:6,  name:'Hair Color – Ash Blonde',      cat:'Hair',    stock:7,  min:5,  price:380,  unit:'tube', supplier:'Wella PH' },
  { id:7,  name:'Argan Oil Serum 100ml',        cat:'Hair',    stock:9,  min:5,  price:650,  unit:'btl',  supplier:'Wella PH' },
  { id:8,  name:'Hyaluronic Serum 30ml',        cat:'Facial',  stock:2,  min:8,  price:980,  unit:'pcs',  supplier:'Derma Supply' },
  { id:9,  name:'Vitamin C Cream 50ml',         cat:'Facial',  stock:11, min:8,  price:750,  unit:'pcs',  supplier:'Derma Supply' },
  { id:10, name:'Massage Oil – Lavender 500ml', cat:'Massage', stock:4,  min:10, price:420,  unit:'btl',  supplier:'Wellness Depot' },
  { id:11, name:'Massage Oil – Eucalyptus',     cat:'Massage', stock:6,  min:10, price:420,  unit:'btl',  supplier:'Wellness Depot' },
  { id:12, name:'Disposable Gloves (box)',      cat:'General', stock:15, min:5,  price:180,  unit:'box',  supplier:'MedSupply PH' },
]
const CATS = ['all','Nail','Hair','Facial','Massage','General']
const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25"
const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"
const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15"
const tdCls = "px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle"

function getStatus(i) { return i.stock === 0 ? 'out' : i.stock < i.min ? 'low' : 'ok' }

export default function AdminInventory() {
  const [inv, setInv] = useState(INIT)
  const [nextId, setNextId] = useState(13)
  const [cat, setCat] = useState('all')
  const [search, setSearch] = useState('')
  const [statusF, setStatusF] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [restockItem, setRestockItem] = useState(null)
  const [restockQty, setRestockQty] = useState(10)
  const [form, setForm] = useState({ name:'', cat:'Nail', unit:'pcs', stock:0, min:5, price:0, supplier:'' })

  const filtered = inv.filter(i => {
    const matchCat = cat === 'all' || i.cat === cat
    const matchSearch = i.name.toLowerCase().includes(search.toLowerCase())
    const matchStatus = !statusF || getStatus(i) === statusF
    return matchCat && matchSearch && matchStatus
  })

  const totalVal = inv.reduce((s,i) => s + i.stock * i.price, 0)

  function addItem() {
    if (!form.name) return alert('Product name required.')
    setInv(prev => [...prev, { ...form, id: nextId, stock: +form.stock, min: +form.min, price: +form.price }])
    setNextId(n => n + 1)
    setAddOpen(false)
    setForm({ name:'', cat:'Nail', unit:'pcs', stock:0, min:5, price:0, supplier:'' })
  }

  function confirmRestock() {
    setInv(prev => prev.map(i => i.id === restockItem.id ? { ...i, stock: i.stock + +restockQty } : i))
    setRestockItem(null)
  }

  function deleteItem(id) {
    if (!confirm('Delete this item?')) return
    setInv(prev => prev.filter(i => i.id !== id))
  }

  const StatusBadge = ({ item }) => {
    const st = getStatus(item)
    const cls = st === 'ok' ? 'bg-[#6fcf97]/15 text-[#6fcf97]' : 'bg-[#eb5757]/15 text-[#eb5757]'
    const label = st === 'out' ? 'Out of Stock' : st === 'low' ? 'Low Stock' : 'In Stock'
    return <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${cls}`}>{label}</span>
  }

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Inventory Management</h1>
          <button onClick={() => setAddOpen(true)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors cursor-pointer border-none">+ Add Item</button>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-6 max-[1024px]:grid-cols-2">
            {[
              { label:'Total Products', value: inv.length },
              { label:'Low Stock', value: inv.filter(i=>getStatus(i)==='low').length, red:true },
              { label:'Out of Stock', value: inv.filter(i=>getStatus(i)==='out').length, red:true },
              { label:'Total Value', value: '₱'+totalVal.toLocaleString() },
            ].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[34px] font-normal leading-none mb-1.5 ${s.red ? 'text-[#eb5757]' : 'text-white'}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Category tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {CATS.map(c => (
              <button key={c} onClick={() => setCat(c)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${cat === c ? 'text-[#f0a800] border-b-[#f0a800]' : 'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </button>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-5 flex-wrap">
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search product..." className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] min-w-[180px] placeholder:text-white/25" />
            <select value={statusF} onChange={e => setStatusF(e.target.value)} className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
              <option value="">All Status</option>
              <option value="ok">In Stock</option>
              <option value="low">Low Stock</option>
              <option value="out">Out of Stock</option>
            </select>
          </div>

          <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['#','Product Name','Category','Stock','Min Level','Unit Price','Total Value','Status','Actions'].map(h=><th key={h} className={thCls}>{h}</th>)}</tr></thead>
              <tbody>
                {filtered.length === 0
                  ? <tr><td colSpan={9} className="text-center text-[#6a4a88] py-8">No items found.</td></tr>
                  : filtered.map(i => {
                    const st = getStatus(i)
                    return (
                      <tr key={i.id} className="hover:bg-[#b040d8]/5 transition-colors">
                        <td className={tdCls+' text-[#6a4a88]'}>#{i.id}</td>
                        <td className={tdCls+' font-medium text-white'}>{i.name}</td>
                        <td className={tdCls}>{i.cat}</td>
                        <td className={tdCls+` font-semibold ${st==='ok'?'text-[#6fcf97]':'text-[#eb5757]'}`}>{i.stock} {i.unit}</td>
                        <td className={tdCls+' text-[#9a7ab8]'}>{i.min} {i.unit}</td>
                        <td className={tdCls}>₱{i.price.toLocaleString()}</td>
                        <td className={tdCls+' text-[#f0a800]'}>₱{(i.stock*i.price).toLocaleString()}</td>
                        <td className={tdCls}><StatusBadge item={i} /></td>
                        <td className={tdCls}>
                          <div className="flex gap-1.5">
                            <button onClick={() => { setRestockItem(i); setRestockQty(10) }} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Restock</button>
                            <button onClick={() => deleteItem(i.id)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3.5 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Delete</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
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
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Add Inventory Item</h3>
              <button onClick={() => setAddOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="mb-4"><label className={labelCls}>Product Name</label><input value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} placeholder="e.g. OPI Gel Polish" className={inputCls} /></div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Category</label>
                  <select value={form.cat} onChange={e=>setForm(f=>({...f,cat:e.target.value}))} className={inputCls}>
                    {['Nail','Hair','Facial','Massage','General'].map(c=><option key={c}>{c}</option>)}
                  </select>
                </div>
                <div><label className={labelCls}>Unit</label><input value={form.unit} onChange={e=>setForm(f=>({...f,unit:e.target.value}))} placeholder="pcs / btl / ml" className={inputCls} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className={labelCls}>Current Stock</label><input type="number" value={form.stock} onChange={e=>setForm(f=>({...f,stock:e.target.value}))} min="0" className={inputCls} /></div>
                <div><label className={labelCls}>Minimum Level</label><input type="number" value={form.min} onChange={e=>setForm(f=>({...f,min:e.target.value}))} min="0" className={inputCls} /></div>
              </div>
              <div className="mb-4"><label className={labelCls}>Unit Price (₱)</label><input type="number" value={form.price} onChange={e=>setForm(f=>({...f,price:e.target.value}))} min="0" step="0.01" className={inputCls} /></div>
              <div><label className={labelCls}>Supplier</label><input value={form.supplier} onChange={e=>setForm(f=>({...f,supplier:e.target.value}))} placeholder="Supplier name" className={inputCls} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={() => setAddOpen(false)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={addItem} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Save Item</button>
            </div>
          </div>
        </div>
      )}

      {/* Restock Modal */}
      {restockItem && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e => e.target === e.currentTarget && setRestockItem(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[380px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Restock Item</h3>
              <button onClick={() => setRestockItem(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <p className="text-[#e0c8f0] text-[13px] mb-4">{restockItem.name}</p>
              <label className={labelCls}>Add Quantity</label>
              <input type="number" value={restockQty} onChange={e => setRestockQty(e.target.value)} min="1" className={inputCls} />
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={() => setRestockItem(null)} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Cancel</button>
              <button onClick={confirmRestock} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Restock</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
