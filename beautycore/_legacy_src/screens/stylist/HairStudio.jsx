import { useState } from 'react'
import StylistSidebar from '../../components/StylistSidebar'

const styles = [
  { name:'Balayage',           category:'Color',     length:'Medium/Long', time:'3h',   price:'₱2,500', popular:true  },
  { name:'Tape-In Extensions', category:'Extension', length:'Any',         time:'2h',   price:'₱3,500', popular:true  },
  { name:'Japanese Head Spa',  category:'Treatment', length:'Any',         time:'1h',   price:'₱600',   popular:true  },
  { name:'Keratin Treatment',  category:'Treatment', length:'Any',         time:'2.5h', price:'₱1,800', popular:false },
  { name:'Highlights',         category:'Color',     length:'Medium/Long', time:'2h',   price:'₱1,500', popular:false },
  { name:'Clip-In Extensions', category:'Extension', length:'Any',         time:'1h',   price:'₱1,200', popular:false },
  { name:'Hair Rebonding',     category:'Treatment', length:'Long',        time:'4h',   price:'₱2,000', popular:false },
  { name:'Ombre Color',        category:'Color',     length:'Medium/Long', time:'2.5h', price:'₱2,000', popular:true  },
]

const catConfig = {
  Color:     { badge:'bg-[#f0a800]/15 text-[#f0a800]' },
  Extension: { badge:'bg-[#7b2fa0]/25 text-[#d060f0]' },
  Treatment: { badge:'bg-[#6fcf97]/15 text-[#6fcf97]' },
}

const categories = ['All','Color','Extension','Treatment']

export default function StylistHairStudio() {
  const [active, setActive] = useState('All')
  const filtered = active === 'All' ? styles : styles.filter(s => s.category === active)

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Hair Style Catalog</h1>
          <div className="flex gap-2">
            {categories.map(c => (
              <button key={c} onClick={() => setActive(c)}
                className={`font-sans text-[9px] font-bold tracking-[1.5px] uppercase px-3.5 py-1.5 border transition-all cursor-pointer
                  ${active===c ? 'bg-[#f0a800] text-[#1a0a2e] border-[#f0a800]' : 'bg-transparent text-[#9a7ab8] border-[#b040d8]/30 hover:border-[#f0a800] hover:text-[#f0a800]'}`}>
                {c}
              </button>
            ))}
          </div>
        </header>

        <div className="p-8">
          <p className="text-[#9a7ab8] text-xs mb-6">Browse hair services and styles to guide client consultations.</p>
          <div className="grid grid-cols-4 gap-5 max-[1200px]:grid-cols-3 max-[900px]:grid-cols-2">
            {filtered.map(s => {
              const cfg = catConfig[s.category]
              return (
                <div key={s.name} className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-hidden hover:border-[#f0a800]/40 transition-all group">
                  <div className="w-full h-[90px] bg-[#b040d8]/10 flex items-center justify-center relative">
                    <span className="text-3xl">💇</span>
                    {s.popular && (
                      <span className="absolute top-2 right-2 font-sans text-[7.5px] font-bold tracking-[1px] uppercase bg-[#f0a800] text-[#1a0a2e] px-1.5 py-0.5">
                        Popular
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    <p className="text-white text-xs font-semibold mb-0.5 group-hover:text-[#f0a800] transition-colors">{s.name}</p>
                    <p className="text-[#9a7ab8] text-[10px] mb-3">{s.length} · {s.time}</p>
                    <div className="flex items-center justify-between">
                      <span className={`font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${cfg.badge}`}>{s.category}</span>
                      <span className="text-[#f0a800] text-xs font-bold">{s.price}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
