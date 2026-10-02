import { useState } from 'react'
import StylistSidebar from '../../components/StylistSidebar'

const designs = [
  { name:'French Tip',      category:'Classic',  color:'White/Pink',  time:'45 min',  price:'₱250', popular:true  },
  { name:'Ombre Gradient',  category:'Trending', color:'Pink/Purple', time:'60 min',  price:'₱350', popular:true  },
  { name:'Floral Art',      category:'Artistic', color:'Multi',       time:'90 min',  price:'₱500', popular:false },
  { name:'Nude Minimalist', category:'Classic',  color:'Nude',        time:'45 min',  price:'₱280', popular:false },
  { name:'Glitter Gel',     category:'Trending', color:'Gold/Silver', time:'60 min',  price:'₱380', popular:true  },
  { name:'3D Nail Art',     category:'Artistic', color:'Custom',      time:'120 min', price:'₱700', popular:false },
  { name:'Marble Effect',   category:'Trending', color:'White/Grey',  time:'75 min',  price:'₱450', popular:true  },
  { name:'Pastel Set',      category:'Classic',  color:'Pastel',      time:'50 min',  price:'₱300', popular:false },
]

const catConfig = {
  Classic:  { badge:'bg-[#6fcf97]/15 text-[#6fcf97]' },
  Trending: { badge:'bg-[#f0a800]/15 text-[#f0a800]' },
  Artistic: { badge:'bg-[#7b2fa0]/25 text-[#d060f0]' },
}

const categories = ['All','Classic','Trending','Artistic']

export default function StylistNailStudio() {
  const [active, setActive] = useState('All')
  const filtered = active === 'All' ? designs : designs.filter(d => d.category === active)

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <StylistSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Nail Design Catalog</h1>
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
          <p className="text-[#9a7ab8] text-xs mb-6">Browse available nail designs to recommend to clients during consultations.</p>
          <div className="grid grid-cols-4 gap-5 max-[1200px]:grid-cols-3 max-[900px]:grid-cols-2">
            {filtered.map(d => {
              const cfg = catConfig[d.category]
              return (
                <div key={d.name} className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-hidden hover:border-[#f0a800]/40 transition-all group">
                  <div className="w-full h-[90px] bg-[#b040d8]/10 flex items-center justify-center relative">
                    <span className="text-3xl">💅</span>
                    {d.popular && (
                      <span className="absolute top-2 right-2 font-sans text-[7.5px] font-bold tracking-[1px] uppercase bg-[#f0a800] text-[#1a0a2e] px-1.5 py-0.5">
                        Popular
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    <p className="text-white text-xs font-semibold mb-0.5 group-hover:text-[#f0a800] transition-colors">{d.name}</p>
                    <p className="text-[#9a7ab8] text-[10px] mb-3">{d.color} · {d.time}</p>
                    <div className="flex items-center justify-between">
                      <span className={`font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${cfg.badge}`}>{d.category}</span>
                      <span className="text-[#f0a800] text-xs font-bold">{d.price}</span>
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
