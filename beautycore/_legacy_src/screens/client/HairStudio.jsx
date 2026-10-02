import { useState } from 'react'
import ClientSidebar from '../../components/ClientSidebar'

const HAIR_STYLES = [
  { id:1,  name:'Soft Layers',        type:'Cut',       length:'Long',   desc:'Effortless long layers with face-framing pieces',  gradient:'linear-gradient(135deg,#3d2314,#8b5e3c)' },
  { id:2,  name:'Bob Cut',            type:'Cut',       length:'Short',  desc:'Classic chin-length bob, sleek and modern',         gradient:'linear-gradient(135deg,#1a1a1a,#555)' },
  { id:3,  name:'Lob (Long Bob)',     type:'Cut',       length:'Medium', desc:'Versatile shoulder-length cut with movement',       gradient:'linear-gradient(135deg,#5c3d2e,#a07850)' },
  { id:4,  name:'Ash Blonde Balayage',type:'Color',     length:'Long',   desc:'Sun-kissed ash blonde with natural grow-out',       gradient:'linear-gradient(135deg,#c8a87a,#e8d5b0)' },
  { id:5,  name:'Chocolate Brown',    type:'Color',     length:'Medium', desc:'Rich, dimensional chocolate brown all-over color',  gradient:'linear-gradient(135deg,#3d1c02,#7b4a2d)' },
  { id:6,  name:'Rose Gold Highlights',type:'Color',    length:'Long',   desc:'Warm rose gold highlights on a light base',        gradient:'linear-gradient(135deg,#e8607a,#f0a800)' },
  { id:7,  name:'Keratin Smoothing',  type:'Treatment', length:'Long',   desc:'Frizz-free, silky smooth finish lasting 3 months',  gradient:'linear-gradient(135deg,#2d1054,#7b2fa0)' },
  { id:8,  name:'Tape-In Extensions', type:'Extension', length:'Long',   desc:'Seamless length and volume with tape-in method',    gradient:'linear-gradient(135deg,#5c3d2e,#c8a87a)' },
  { id:9,  name:'Bridal Updo',        type:'Style',     length:'Long',   desc:'Elegant updo perfect for weddings and events',      gradient:'linear-gradient(135deg,#f0a800,#fff3c0)' },
  { id:10, name:'Beach Waves',        type:'Style',     length:'Medium', desc:'Effortless tousled waves for a relaxed look',       gradient:'linear-gradient(135deg,#c8a87a,#f0a800)' },
  { id:11, name:'Pixie Cut',          type:'Cut',       length:'Short',  desc:'Bold and chic ultra-short pixie cut',               gradient:'linear-gradient(135deg,#1a1a1a,#7b2fa0)' },
  { id:12, name:'Purple Fantasy',     type:'Color',     length:'Long',   desc:'Vivid purple fantasy color with gradient fade',     gradient:'linear-gradient(135deg,#7b2fa0,#d060f0)' },
]
const HAIR_COLORS = [
  { name:'Black', hex:'#1a1a1a' }, { name:'Dark Brown', hex:'#3d1c02' }, { name:'Brown', hex:'#7b4a2d' }, { name:'Light Brown', hex:'#a07850' },
  { name:'Dirty Blonde', hex:'#c8a87a' }, { name:'Blonde', hex:'#e8d5b0' }, { name:'Ash Blonde', hex:'#d4c9a8' }, { name:'Red', hex:'#8b2500' },
  { name:'Auburn', hex:'#a0522d' }, { name:'Rose Gold', hex:'#e8607a' }, { name:'Purple', hex:'#7b2fa0' }, { name:'Platinum', hex:'#f0ece0' },
]
const TECHNIQUES = ['Balayage','Highlights','Ombre','Full Color','Toner','Bleach & Tone']
const HAIR_SERVICES = ["Women's Cut & Blowdry","Men's Cut","Full Colour","Balayage","Highlights","Keratin Treatment","Hair Extensions","Bridal Hair"]

export default function HairStudio() {
  const [tab, setTab] = useState('styles')
  const [search, setSearch] = useState('')
  const [typeF, setTypeF] = useState('')
  const [lengthF, setLengthF] = useState('')
  const [saved, setSaved] = useState([])
  const [colorState, setColorState] = useState({ base:HAIR_COLORS[2], target:HAIR_COLORS[4], technique:'Balayage' })
  const [bookOpen, setBookOpen] = useState(false)
  const [toast, setToast] = useState('')

  function showToast(msg) { setToast(msg); setTimeout(()=>setToast(''),2500) }

  const filtered = HAIR_STYLES.filter(d => {
    return (!search || d.name.toLowerCase().includes(search.toLowerCase())) &&
           (!typeF   || d.type === typeF) &&
           (!lengthF || d.length === lengthF)
  })

  function saveStyle(d) {
    if (saved.find(s=>s.id===d.id)) return showToast('Already saved.')
    setSaved(prev=>[...prev,d]); showToast('Look saved!')
  }

  function saveColorLook() {
    const look = { id:Date.now(), name:`${colorState.base.name} → ${colorState.target.name}`, type:'Color', length:'Custom', desc:colorState.technique, gradient:`linear-gradient(135deg,${colorState.base.hex},${colorState.target.hex})` }
    setSaved(prev=>[...prev,look]); showToast('Color look saved!')
  }

  function removeSaved(id) { setSaved(prev=>prev.filter(d=>d.id!==id)) }

  const btnCls = "font-sans text-[9px] font-bold tracking-[1.5px] uppercase px-3.5 py-1.5 cursor-pointer transition-all"
  const goldBtn = btnCls + " bg-[#f0a800] text-[#1a0a2e] border-none hover:bg-[#f5c040]"
  const outBtn  = btnCls + " bg-transparent border border-[#b040d8]/40 text-[#c8a8e0] hover:border-[#f0a800] hover:text-[#f0a800]"
  const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25"

  const StyleCard = ({ d, onSave, onRemove }) => (
    <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-hidden transition-all duration-200 hover:border-[#f0a800]/40 hover:-translate-y-0.5">
      <div className="h-[140px]" style={{ background:d.gradient }} />
      <div className="p-4">
        <p className="font-serif text-[16px] font-normal text-white mb-2">{d.name}</p>
        <div className="flex gap-1.5 flex-wrap mb-2">
          {[d.type, d.length||d.desc].filter(Boolean).map(t=>(
            <span key={t} className="font-sans text-[9px] font-semibold tracking-[1px] uppercase text-[#9a7ab8] bg-[#b040d8]/10 px-2 py-[3px]">{t}</span>
          ))}
        </div>
        {d.desc && d.type !== 'Color' && <p className="font-sans text-[11px] text-[#9a7ab8] mb-2.5 leading-[1.5]">{d.desc}</p>}
        <div className="flex gap-2">
          {onSave && <button className={outBtn+' flex-1'} onClick={()=>onSave(d)}>Save</button>}
          {onRemove && <button className={btnCls+' flex-1 bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 hover:bg-[#eb5757]/25'} onClick={()=>onRemove(d.id)}>Remove</button>}
          <button className={goldBtn+' flex-1'} onClick={()=>setBookOpen(true)}>Book</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Hair Studio</h1>
          <button onClick={()=>setBookOpen(true)} className={goldBtn}>Book Hair Service</button>
        </header>

        <div className="p-8 flex-1">
          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {[['styles','Browse Styles'],['color','Color Picker'],['hsaved','Saved Looks']].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${tab===t?'text-[#f0a800] border-b-[#f0a800]':'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {l}
              </button>
            ))}
          </div>

          {/* BROWSE STYLES */}
          {tab === 'styles' && (
            <div>
              <div className="flex gap-3 mb-5 flex-wrap">
                <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search styles..." className={inputCls+' min-w-[180px]'} />
                <select value={typeF} onChange={e=>setTypeF(e.target.value)} className={inputCls}>
                  <option value="">All Types</option>
                  {['Cut','Color','Treatment','Extension','Style'].map(t=><option key={t}>{t}</option>)}
                </select>
                <select value={lengthF} onChange={e=>setLengthF(e.target.value)} className={inputCls}>
                  <option value="">All Lengths</option>
                  {['Short','Medium','Long'].map(l=><option key={l}>{l}</option>)}
                </select>
              </div>
              <div className="grid gap-5" style={{ gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))' }}>
                {filtered.map(d=><StyleCard key={d.id} d={d} onSave={saveStyle} />)}
              </div>
            </div>
          )}

          {/* COLOR PICKER */}
          {tab === 'color' && (
            <div className="grid grid-cols-2 gap-6 max-[1024px]:grid-cols-1">
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Hair Color Selector</h2></div>
                <div className="p-6">
                  {[['Natural Base','base'],['Target Color','target']].map(([label,key])=>(
                    <div key={key} className="mb-5">
                      <p className="font-sans text-[10px] font-bold tracking-[2px] uppercase text-[#c8a8e0] mb-2.5">{label}</p>
                      <div className="flex flex-wrap gap-2">
                        {HAIR_COLORS.map(c=>(
                          <div key={c.name} onClick={()=>setColorState(s=>({...s,[key]:c}))}
                            className={`w-7 h-7 rounded-full cursor-pointer border-2 transition-all duration-150 hover:scale-110 ${colorState[key].name===c.name?'border-[#f0a800] scale-110':'border-transparent'}`}
                            style={{ background:c.hex }} title={c.name} />
                        ))}
                      </div>
                    </div>
                  ))}
                  <div className="mb-5">
                    <p className="font-sans text-[10px] font-bold tracking-[2px] uppercase text-[#c8a8e0] mb-2.5">Technique</p>
                    <div className="flex flex-wrap gap-2">
                      {TECHNIQUES.map(t=>(
                        <button key={t} onClick={()=>setColorState(s=>({...s,technique:t}))}
                          className={`font-sans text-[10px] font-semibold tracking-[1px] uppercase px-3 py-1.5 border cursor-pointer transition-all duration-150 ${colorState.technique===t?'bg-[#f0a800]/12 border-[#f0a800] text-[#f0a800]':'bg-[#b040d8]/8 border-[#b040d8]/25 text-[#9a7ab8] hover:border-[#f0a800] hover:text-[#f0a800]'}`}>
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button onClick={saveColorLook} className={outBtn+' flex-1'}>Save Look</button>
                    <button onClick={()=>setBookOpen(true)} className={goldBtn+' flex-1'}>Book Now</button>
                  </div>
                </div>
              </div>

              {/* Preview */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Color Preview</h2></div>
                <div className="p-6 flex flex-col items-center gap-5">
                  <div className="relative w-[120px] h-[180px] flex flex-col items-center">
                    <div className="absolute top-0 w-[90px] h-[140px] rounded-[50%_50%_30%_30%] z-[1] transition-all duration-400"
                      style={{ background:`linear-gradient(180deg,${colorState.base.hex} 0%,${colorState.target.hex} 100%)` }} />
                    <div className="w-[70px] h-[80px] bg-[#d4a574] rounded-[50%_50%_45%_45%] relative z-[2] mt-10" />
                  </div>
                  <div className="text-center">
                    <p className="font-serif text-[20px] text-white mb-2">{colorState.base.name} → {colorState.target.name}</p>
                    <p className="font-sans text-[11px] text-[#9a7ab8] tracking-[1px]">{colorState.technique}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SAVED LOOKS */}
          {tab === 'hsaved' && (
            saved.length === 0
              ? <p className="text-center py-12 text-[#6a4a88] text-[13px] leading-[1.7]">No saved looks yet. <button onClick={()=>setTab('styles')} className="text-[#f0a800] bg-none border-none cursor-pointer">Browse styles</button> or use the <button onClick={()=>setTab('color')} className="text-[#f0a800] bg-none border-none cursor-pointer">Color Picker</button>.</p>
              : <div className="grid gap-5" style={{ gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))' }}>
                  {saved.map(d=><StyleCard key={d.id} d={d} onRemove={removeSaved} />)}
                </div>
          )}
        </div>
      </div>

      {/* Book Modal */}
      {bookOpen && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e=>e.target===e.currentTarget&&setBookOpen(false)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[440px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Book Hair Service</h3>
              <button onClick={()=>setBookOpen(false)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Service Type</label>
                <select className={inputCls}>{HAIR_SERVICES.map(s=><option key={s}>{s}</option>)}</select>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Date</label><input type="date" className={inputCls} /></div>
                <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Time</label>
                  <select className={inputCls}>{['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM'].map(t=><option key={t}>{t}</option>)}</select>
                </div>
              </div>
              <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Reference / Notes</label><textarea rows={3} placeholder="Describe your desired look..." className={inputCls+' resize-none'} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={()=>setBookOpen(false)} className={outBtn}>Cancel</button>
              <button onClick={()=>{ setBookOpen(false); showToast('Hair booking submitted!') }} className={goldBtn}>Confirm Booking</button>
            </div>
          </div>
        </div>
      )}

      {toast && <div className="fixed bottom-8 right-8 bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[1.5px] px-6 py-3 z-[9999]">{toast}</div>}
    </div>
  )
}
