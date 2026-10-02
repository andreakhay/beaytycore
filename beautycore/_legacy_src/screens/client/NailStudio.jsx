import { useState } from 'react'
import ClientSidebar from '../../components/ClientSidebar'

// ─── PRICING ─────────────────────────────────────────────────────────────────
const PRESET_PRICES = {
  1:180, 2:350, 3:280, 4:550, 5:750, 6:350, 7:480, 8:220, 9:400, 10:180, 11:650, 12:500
}
const FINISH_PRICE = { Glossy:0, Matte:50, Shimmer:80, Glitter:100, Chrome:150, Velvet:120 }
const ART_PRICE    = { None:0, 'French Tip':80, Floral:150, Abstract:200, Geometric:180, Marble:220, Ombre:160, 'Glitter Tips':120 }

const COLORS = [
  { name:'Nude', hex:'#e8c9a0' }, { name:'Blush', hex:'#f4a7b9' }, { name:'Rose', hex:'#e8607a' }, { name:'Red', hex:'#c0392b' },
  { name:'Berry', hex:'#8e44ad' }, { name:'Purple', hex:'#7b2fa0' }, { name:'Navy', hex:'#2c3e7a' }, { name:'Black', hex:'#1a1a1a' },
  { name:'White', hex:'#f5f5f5' }, { name:'Gold', hex:'#f0a800' }, { name:'Coral', hex:'#e8735a' }, { name:'Mint', hex:'#7ecba1' },
]
const SHAPES   = ['Round','Square','Oval','Almond','Stiletto','Coffin']
const FINISHES = ['Glossy','Matte','Shimmer','Glitter','Chrome','Velvet']
const ARTS     = ['None','French Tip','Floral','Abstract','Geometric','Marble','Ombre','Glitter Tips']
const PRESETS  = [
  { id:1,  name:'Nude Minimalist',    style:'Minimalist', color:'Nude',   base:'#e8c9a0', accent:'#d4b080', shape:'Oval',    finish:'Matte',   art:'None',         gradient:'linear-gradient(135deg,#e8c9a0,#d4b080)', rating:4.8, popular:false },
  { id:2,  name:'Rose Gold Glam',     style:'Glitter',    color:'Gold',   base:'#f0a800', accent:'#e8607a', shape:'Almond',  finish:'Shimmer', art:'Glitter Tips', gradient:'linear-gradient(135deg,#f0a800,#e8607a)', rating:4.9, popular:true  },
  { id:3,  name:'French Classic',     style:'French',     color:'White',  base:'#f5f5f5', accent:'#e8c9a0', shape:'Square',  finish:'Glossy',  art:'French Tip',   gradient:'linear-gradient(135deg,#f5f5f5,#e8c9a0)', rating:4.7, popular:true  },
  { id:4,  name:'Berry Ombre',        style:'Ombre',      color:'Purple', base:'#8e44ad', accent:'#e8607a', shape:'Coffin',  finish:'Glossy',  art:'Ombre',        gradient:'linear-gradient(135deg,#8e44ad,#e8607a)', rating:4.6, popular:false },
  { id:5,  name:'Midnight Black',     style:'Minimalist', color:'Black',  base:'#1a1a1a', accent:'#f0a800', shape:'Stiletto',finish:'Chrome',  art:'None',         gradient:'linear-gradient(135deg,#1a1a1a,#f0a800)', rating:4.5, popular:false },
  { id:6,  name:'Floral Blush',       style:'Floral',     color:'Pink',   base:'#f4a7b9', accent:'#f5f5f5', shape:'Round',   finish:'Glossy',  art:'Floral',       gradient:'linear-gradient(135deg,#f4a7b9,#f5f5f5)', rating:4.8, popular:true  },
  { id:7,  name:'Purple Marble',      style:'Abstract',   color:'Purple', base:'#7b2fa0', accent:'#f5f5f5', shape:'Oval',    finish:'Matte',   art:'Marble',       gradient:'linear-gradient(135deg,#7b2fa0,#c8a8e0)', rating:4.7, popular:false },
  { id:8,  name:'Coral Summer',       style:'Seasonal',   color:'Red',    base:'#e8735a', accent:'#f0a800', shape:'Round',   finish:'Glossy',  art:'None',         gradient:'linear-gradient(135deg,#e8735a,#f0a800)', rating:4.4, popular:false },
  { id:9,  name:'Navy Geometric',     style:'Abstract',   color:'Black',  base:'#2c3e7a', accent:'#f5f5f5', shape:'Square',  finish:'Matte',   art:'Geometric',    gradient:'linear-gradient(135deg,#2c3e7a,#5b7fc4)', rating:4.3, popular:false },
  { id:10, name:'Mint Fresh',         style:'Minimalist', color:'White',  base:'#7ecba1', accent:'#f5f5f5', shape:'Round',   finish:'Glossy',  art:'None',         gradient:'linear-gradient(135deg,#7ecba1,#b8e8d0)', rating:4.6, popular:false },
  { id:11, name:'Red Velvet',         style:'Minimalist', color:'Red',    base:'#c0392b', accent:'#8e44ad', shape:'Almond',  finish:'Velvet',  art:'None',         gradient:'linear-gradient(135deg,#c0392b,#8e44ad)', rating:4.5, popular:false },
  { id:12, name:'Gold Glitter',       style:'Glitter',    color:'Gold',   base:'#f0a800', accent:'#f5f5f5', shape:'Coffin',  finish:'Glitter', art:'Glitter Tips', gradient:'linear-gradient(135deg,#f0a800,#fff3c0)', rating:4.9, popular:false },
]
const SHAPE_RADIUS = { Round:'50% 50% 40% 40%', Square:'4px', Oval:'50% 50% 35% 35%', Almond:'50% 50% 30% 30%', Stiletto:'50% 50% 10% 10%', Coffin:'20% 20% 5% 5%' }

const STYLES_LIST = ['Minimalist','Floral','Glitter','French','Ombre','Abstract','Seasonal']
const COLOR_LIST  = ['Nude','Pink','Red','Purple','White','Black','Gold']

export default function NailStudio() {
  const [tab, setTab] = useState('browse')
  const [search, setSearch] = useState('')
  const [catF, setCatF] = useState('')
  const [colorF, setColorF] = useState('')
  const [saved, setSaved] = useState([])
  const [builder, setBuilder] = useState({ base:COLORS[0], accent:COLORS[9], shape:'Oval', finish:'Glossy', art:'None', name:'' })
  const [bookDesign, setBookDesign] = useState(null)
  const [toast, setToast] = useState('')

  function showToast(msg) { setToast(msg); setTimeout(()=>setToast(''),2500) }

  const filtered = PRESETS.filter(d => {
    const matchSearch = d.name.toLowerCase().includes(search.toLowerCase())
    const matchCat    = !catF   || d.style === catF
    const matchColor  = !colorF || d.color === colorF
    return matchSearch && matchCat && matchColor
  })

  function saveDesign(d) {
    if (saved.find(s=>s.id===d.id)) return showToast('Already saved.')
    setSaved(prev=>[...prev,d]); showToast('Design saved!')
  }

  function removeSaved(id) { setSaved(prev=>prev.filter(d=>d.id!==id)) }

  function saveCustom() {
    const name = builder.name.trim() || 'Custom Design'
    const d = { id:Date.now(), name, style:'Custom', color:builder.base.name, base:builder.base.hex, accent:builder.accent.hex, shape:builder.shape, finish:builder.finish, art:builder.art, gradient:`linear-gradient(135deg,${builder.base.hex},${builder.accent.hex})` }
    setSaved(prev=>[...prev,d]); showToast('Design saved!')
  }

  const btnCls = "font-sans text-[9px] font-bold tracking-[1.5px] uppercase px-3.5 py-1.5 cursor-pointer transition-all"
  const goldBtn = btnCls + " bg-[#f0a800] text-[#1a0a2e] border-none hover:bg-[#f5c040]"
  const outBtn  = btnCls + " bg-transparent border border-[#b040d8]/40 text-[#c8a8e0] hover:border-[#f0a800] hover:text-[#f0a800]"
  const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25"

  const DesignCard = ({ d, onSave, onRemove }) => (
    <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-hidden transition-all duration-200 hover:border-[#f0a800]/40 hover:-translate-y-0.5">
      <div className="h-[140px] flex items-center justify-center relative" style={{ background:d.gradient }}>
        <div className="flex gap-1.5 items-end">
          {[0,1,2,3,4].map(i=>(
            <div key={i} className="w-[18px] shadow-md" style={{ height:i===2?'34px':i===0||i===4?'22px':'28px', background:i===2?d.accent:d.base, borderRadius:SHAPE_RADIUS[d.shape]||'50% 50% 40% 40%' }} />
          ))}
        </div>
      </div>
      <div className="p-4">
        <p className="font-serif text-[16px] font-normal text-white mb-2">{d.name}</p>
        <div className="flex gap-1.5 flex-wrap mb-2.5">
          {[d.style, d.finish, d.shape].filter(Boolean).map(t=>(
            <span key={t} className="font-sans text-[9px] font-semibold tracking-[1px] uppercase text-[#9a7ab8] bg-[#b040d8]/10 px-2 py-[3px]">{t}</span>
          ))}
        </div>
        <div className="flex gap-2">
          {onSave && <button className={outBtn+' flex-1'} onClick={()=>onSave(d)}>Save</button>}
          {onRemove && <button className={btnCls+' flex-1 bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 hover:bg-[#eb5757]/25'} onClick={()=>onRemove(d.id)}>Remove</button>}
          <button className={goldBtn+' flex-1'} onClick={()=>setBookDesign(d.name)}>Book</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Nail Studio</h1>
          <div className="flex gap-2">
            <button onClick={()=>setTab('saved')} className={outBtn}>Saved Designs</button>
            <button onClick={()=>setTab('custom')} className={goldBtn}>+ Custom Design</button>
          </div>
        </header>

        <div className="p-8 flex-1">
          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {[['browse','Browse Designs'],['custom','Custom Builder'],['saved','Saved Designs']].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${tab===t?'text-[#f0a800] border-b-[#f0a800]':'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {l}
              </button>
            ))}
          </div>

          {/* BROWSE */}
          {tab === 'browse' && (
            <div>
              <div className="flex gap-3 mb-5 flex-wrap">
                <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search designs..." className={inputCls+' min-w-[180px]'} />
                <select value={catF} onChange={e=>setCatF(e.target.value)} className={inputCls}>
                  <option value="">All Styles</option>
                  {STYLES_LIST.map(s=><option key={s}>{s}</option>)}
                </select>
                <select value={colorF} onChange={e=>setColorF(e.target.value)} className={inputCls}>
                  <option value="">All Colors</option>
                  {COLOR_LIST.map(c=><option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="grid gap-5" style={{ gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))' }}>
                {filtered.map(d=><DesignCard key={d.id} d={d} onSave={saveDesign} />)}
              </div>
            </div>
          )}

          {/* CUSTOM BUILDER */}
          {tab === 'custom' && (
            <div className="grid grid-cols-2 gap-6 items-start max-[1024px]:grid-cols-1">
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Design Builder</h2></div>
                <div className="p-6">
                  <div className="mb-5">
                    <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-2">Design Name</label>
                    <input value={builder.name} onChange={e=>setBuilder(b=>({...b,name:e.target.value}))} placeholder="My custom design..." className={inputCls} />
                  </div>
                  {[
                    { label:'Base Color', key:'base', items:COLORS, type:'swatch' },
                    { label:'Accent Color', key:'accent', items:COLORS, type:'swatch' },
                    { label:'Nail Shape', key:'shape', items:SHAPES, type:'btn' },
                    { label:'Finish', key:'finish', items:FINISHES, type:'btn' },
                    { label:'Art Style', key:'art', items:ARTS, type:'btn' },
                  ].map(({ label, key, items, type }) => (
                    <div key={key} className="mb-4">
                      <p className="font-sans text-[10px] font-bold tracking-[2px] uppercase text-[#c8a8e0] mb-2.5">{label}</p>
                      <div className="flex flex-wrap gap-2">
                        {type === 'swatch'
                          ? items.map(c=>(
                            <div key={c.name} onClick={()=>setBuilder(b=>({...b,[key]:c}))}
                              className={`w-7 h-7 rounded-full cursor-pointer border-2 transition-all duration-150 hover:scale-110 ${builder[key].name===c.name?'border-[#f0a800] scale-110':'border-transparent'}`}
                              style={{ background:c.hex }} title={c.name} />
                          ))
                          : items.map(item=>(
                            <button key={item} onClick={()=>setBuilder(b=>({...b,[key]:item}))}
                              className={`font-sans text-[10px] font-semibold tracking-[1px] uppercase px-3 py-1.5 border cursor-pointer transition-all duration-150 ${builder[key]===item?'bg-[#f0a800]/12 border-[#f0a800] text-[#f0a800]':'bg-[#b040d8]/8 border-[#b040d8]/25 text-[#9a7ab8] hover:border-[#f0a800] hover:text-[#f0a800]'}`}>
                              {item}
                            </button>
                          ))
                        }
                      </div>
                    </div>
                  ))}
                  <div className="flex gap-3 mt-6">
                    <button onClick={()=>setBuilder({base:COLORS[0],accent:COLORS[9],shape:'Oval',finish:'Glossy',art:'None',name:''})} className={outBtn+' flex-1'}>Reset</button>
                    <button onClick={saveCustom} className={goldBtn+' flex-1'}>Save Design</button>
                  </div>
                  <button onClick={()=>setBookDesign(builder.name||'Custom Design')} className={goldBtn+' w-full mt-2.5'}>Book with This Design</button>
                </div>
              </div>

              {/* Preview */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12"><h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Live Preview</h2></div>
                <div className="p-6 flex flex-col items-center gap-6">
                  <div className="flex gap-2.5 items-end p-6 bg-[#b040d8]/5 border border-[#b040d8]/15">
                    {[0,1,2,3,4].map(i=>(
                      <div key={i} className="w-9 shadow-lg transition-all duration-300"
                        style={{ height:i===2?'72px':i===0||i===4?'48px':'60px', background:i===2?builder.accent.hex:builder.base.hex, borderRadius:SHAPE_RADIUS[builder.shape]||'50% 50% 40% 40%' }} />
                    ))}
                  </div>
                  <div className="text-center">
                    <p className="font-serif text-[20px] text-white mb-2">{builder.name||'My Design'}</p>
                    <div className="flex gap-2 flex-wrap justify-center">
                      {[builder.shape, builder.finish, builder.art!=='None'?builder.art:null].filter(Boolean).map(t=>(
                        <span key={t} className="font-sans text-[9px] font-semibold tracking-[1px] uppercase text-[#9a7ab8] bg-[#b040d8]/10 px-2 py-[3px]">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SAVED */}
          {tab === 'saved' && (
            saved.length === 0
              ? <p className="text-center py-12 text-[#6a4a88] text-[13px] leading-[1.7]">No saved designs yet. <button onClick={()=>setTab('browse')} className="text-[#f0a800] bg-none border-none cursor-pointer">Browse designs</button> or <button onClick={()=>setTab('custom')} className="text-[#f0a800] bg-none border-none cursor-pointer">build your own</button>.</p>
              : <div className="grid gap-5" style={{ gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))' }}>
                  {saved.map(d=><DesignCard key={d.id} d={d} onRemove={removeSaved} />)}
                </div>
          )}
        </div>
      </div>

      {/* Book Modal */}
      {bookDesign && (
        <div className="fixed inset-0 bg-[#0a0214]/85 z-[200] flex items-center justify-center p-6" onClick={e=>e.target===e.currentTarget&&setBookDesign(null)}>
          <div className="bg-[#1a0a2e] border border-[#b040d8]/30 w-full max-w-[440px]">
            <div className="px-6 py-5 border-b border-[#b040d8]/15 flex items-center justify-between">
              <h3 className="font-serif text-[20px] font-normal text-white tracking-[1px]">Book Nail Studio</h3>
              <button onClick={()=>setBookDesign(null)} className="bg-none border-none text-[#9a7ab8] text-xl cursor-pointer hover:text-[#f0a800] transition-colors leading-none">✕</button>
            </div>
            <div className="p-6">
              <div className="bg-[#f0a800]/7 border border-[#f0a800]/20 p-3.5 mb-5">
                <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Selected Design</p>
                <p className="text-[#f0a800] text-[14px] font-semibold">{bookDesign}</p>
              </div>
              <div className="grid grid-cols-2 gap-3.5 mb-4">
                <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Date</label><input type="date" className={inputCls} /></div>
                <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Time</label>
                  <select className={inputCls}>
                    {['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM','3:00 PM'].map(t=><option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div><label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Notes</label><textarea rows={2} placeholder="Any additional requests..." className={inputCls+' resize-none'} /></div>
            </div>
            <div className="px-6 py-4 border-t border-[#b040d8]/15 flex gap-3 justify-end">
              <button onClick={()=>setBookDesign(null)} className={outBtn}>Cancel</button>
              <button onClick={()=>{ setBookDesign(null); showToast('Booking submitted for '+bookDesign) }} className={goldBtn}>Confirm Booking</button>
            </div>
          </div>
        </div>
      )}

      {toast && <div className="fixed bottom-8 right-8 bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[1.5px] px-6 py-3 z-[9999]">{toast}</div>}
    </div>
  )
}
