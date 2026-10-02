import AdminSidebar from '../../components/AdminSidebar'

const trendingServices = [
  { rank:1, name:'HydraFacial', category:'Facial', growth:'+34%', demand:'Very High', searches:1240, color:'#6fcf97' },
  { rank:2, name:'Balayage', category:'Hair', growth:'+28%', demand:'High', searches:980, color:'#f0a800' },
  { rank:3, name:'Gel Manicure', category:'Nails', growth:'+22%', demand:'High', searches:870, color:'#b040d8' },
  { rank:4, name:'Japanese Head Spa', category:'Spa', growth:'+19%', demand:'High', searches:760, color:'#7b2fa0' },
  { rank:5, name:'Lash Extensions', category:'Makeup', growth:'+17%', demand:'Medium', searches:640, color:'#e8607a' },
  { rank:6, name:'Microneedling', category:'Facial', growth:'+15%', demand:'Medium', searches:520, color:'#f5c040' },
]

const monthlyData = [
  { month:'Nov', revenue:42000, clients:89 },
  { month:'Dec', revenue:68000, clients:134 },
  { month:'Jan', revenue:51000, clients:102 },
  { month:'Feb', revenue:55000, clients:110 },
  { month:'Mar', revenue:63000, clients:128 },
  { month:'Apr', revenue:71000, clients:147 },
  { month:'May', revenue:78000, clients:158 },
]

const maxRevenue = Math.max(...monthlyData.map(d => d.revenue))

const insights = [
  { icon:'📈', title:'Peak Season Approaching', desc:'June–August historically shows 40% higher bookings. Consider hiring seasonal staff and stocking up on supplies.', type:'opportunity' },
  { icon:'💅', title:'Nail Services Trending Up', desc:'Gel manicures and nail art searches increased 22% this month. Expanding nail service offerings could boost revenue.', type:'opportunity' },
  { icon:'⚠️', title:'Massage Bookings Declining', desc:'Massage therapy bookings dropped 8% vs last month. Consider promotional packages or loyalty discounts.', type:'warning' },
  { icon:'🌟', title:'HydraFacial Demand Surge', desc:'HydraFacial is the #1 trending treatment in your area. Ensure equipment availability and trained staff.', type:'opportunity' },
  { icon:'💰', title:'Average Spend Increasing', desc:'Average client spend rose from ₱850 to ₱1,120 this quarter — a 32% increase. Upselling is working.', type:'positive' },
  { icon:'👥', title:'New Client Acquisition', desc:'12 new clients this month vs 8 last month. Referral program is showing results.', type:'positive' },
]

const competitors = [
  { name:"Glow Studio", location:'Daet Centro', rating:4.2, priceRange:'₱₱', specialty:'Facials & Laser' },
  { name:"Nail Bar PH", location:'Bagasbas', rating:4.0, priceRange:'₱', specialty:'Nail Art' },
  { name:"Serenity Spa", location:'Daet', rating:4.5, priceRange:'₱₱₱', specialty:'Massage & Wellness' },
]

const demandMap = { 'Very High':'bg-[#6fcf97]/15 text-[#6fcf97]', 'High':'bg-[#f0a800]/15 text-[#f0a800]', 'Medium':'bg-[#b040d8]/15 text-[#d060f0]', 'Low':'bg-[#eb5757]/15 text-[#eb5757]' }

export default function AdminMarketTrends() {
  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Market Trend Analysis</h1>
            <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1px]">Last updated: May 7, 2026 · Camarines Norte Region</p>
          </div>
          <span className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#6fcf97]/15 text-[#6fcf97] px-3 py-1.5">LIVE DATA</span>
        </header>

        <div className="p-8 flex-1">

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-5 mb-8 max-[1024px]:grid-cols-2">
            {[
              { label:'Market Growth Rate', value:'+18.4%', sub:'vs last quarter', color:'text-[#6fcf97]' },
              { label:'Avg. Service Price', value:'₱1,120', sub:'+32% vs last year', color:'text-white' },
              { label:'Client Retention', value:'76%', sub:'Industry avg: 62%', color:'text-[#f0a800]' },
              { label:'Trending Category', value:'Facials', sub:'#1 in your area', color:'text-[#d060f0]' },
            ].map(k => (
              <div key={k.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{k.label}</p>
                <p className={`font-serif text-[30px] font-normal leading-none mb-1.5 ${k.color}`}>{k.value}</p>
                <p className="font-sans text-[10px] text-[#9a7ab8]">{k.sub}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-[1.4fr_1fr] gap-6 mb-6">
            {/* Revenue chart */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Revenue Trend (7 Months)</h2>
              </div>
              <div className="p-6">
                <div className="flex items-end gap-3 h-[160px]">
                  {monthlyData.map(d => (
                    <div key={d.month} className="flex-1 flex flex-col items-center gap-1.5">
                      <span className="font-sans text-[9px] text-[#f0a800]">₱{(d.revenue/1000).toFixed(0)}k</span>
                      <div className="w-full rounded-t-sm transition-all duration-500"
                        style={{ height:`${Math.round(d.revenue/maxRevenue*120)}px`, background:'linear-gradient(180deg,#f0a800,#7b2fa0)' }} />
                      <span className="font-sans text-[9px] text-[#9a7ab8]">{d.month}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 pt-4 border-t border-[#b040d8]/12 flex justify-between text-[10px] text-[#9a7ab8]">
                  <span>Total 7-month revenue: <strong className="text-[#f0a800]">₱428,000</strong></span>
                  <span>Avg monthly: <strong className="text-white">₱61,143</strong></span>
                </div>
              </div>
            </div>

            {/* Trending services */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Trending Services</h2>
              </div>
              <div className="p-4 flex flex-col gap-2">
                {trendingServices.map(s => (
                  <div key={s.name} className="flex items-center gap-3 p-2.5 hover:bg-[#b040d8]/5 transition-colors">
                    <span className="font-serif text-[18px] font-normal w-6 text-center" style={{ color: s.color }}>#{s.rank}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-sans text-[11px] font-semibold text-white truncate">{s.name}</p>
                      <p className="font-sans text-[9px] text-[#9a7ab8]">{s.category} · {s.searches} searches</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-sans text-[11px] font-bold text-[#6fcf97]">{s.growth}</p>
                      <span className={`inline-block font-sans text-[8px] font-bold tracking-[1px] uppercase px-1.5 py-[2px] ${demandMap[s.demand]}`}>{s.demand}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Insights */}
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15 mb-6">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center gap-3">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">AI Business Insights</h2>
              <span className="font-sans text-[9px] font-bold tracking-[1px] uppercase bg-[#b040d8]/20 text-[#d060f0] px-2 py-1">AI POWERED</span>
            </div>
            <div className="p-6 grid grid-cols-3 gap-4 max-[1024px]:grid-cols-2">
              {insights.map(ins => (
                <div key={ins.title} className={`p-4 border ${ins.type === 'opportunity' ? 'border-[#f0a800]/20 bg-[#f0a800]/5' : ins.type === 'warning' ? 'border-[#eb5757]/20 bg-[#eb5757]/5' : 'border-[#6fcf97]/20 bg-[#6fcf97]/5'}`}>
                  <div className="text-[20px] mb-2">{ins.icon}</div>
                  <p className="font-sans text-[11px] font-semibold text-white mb-1.5">{ins.title}</p>
                  <p className="font-sans text-[10px] text-[#9a7ab8] leading-[1.6]">{ins.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Competitor analysis */}
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Local Competitor Overview</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr>
                    {['Competitor','Location','Rating','Price Range','Specialty','vs Andrea\'s'].map(h => (
                      <th key={h} className="text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-5 py-3 border-b border-[#b040d8]/15">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {competitors.map(c => (
                    <tr key={c.name} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className="px-5 py-3.5 font-semibold text-white border-b border-[#b040d8]/7">{c.name}</td>
                      <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">{c.location}</td>
                      <td className="px-5 py-3.5 border-b border-[#b040d8]/7">
                        <span className="text-[#f0a800]">{'★'.repeat(Math.floor(c.rating))}</span>
                        <span className="text-[#9a7ab8] ml-1">{c.rating}</span>
                      </td>
                      <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">{c.priceRange}</td>
                      <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">{c.specialty}</td>
                      <td className="px-5 py-3.5 border-b border-[#b040d8]/7">
                        <span className="font-sans text-[9px] font-bold tracking-[1px] uppercase bg-[#6fcf97]/15 text-[#6fcf97] px-2 py-[3px]">ADVANTAGE</span>
                      </td>
                    </tr>
                  ))}
                  {/* Andrea's row */}
                  <tr className="bg-[#f0a800]/5">
                    <td className="px-5 py-3.5 font-semibold text-[#f0a800] border-b border-[#b040d8]/7">Andrea's ⭐</td>
                    <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">Bagasbas Road</td>
                    <td className="px-5 py-3.5 border-b border-[#b040d8]/7"><span className="text-[#f0a800]">★★★★★</span><span className="text-[#9a7ab8] ml-1">4.9</span></td>
                    <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">₱₱</td>
                    <td className="px-5 py-3.5 text-[#e0c8f0] border-b border-[#b040d8]/7">Full Service Clinic</td>
                    <td className="px-5 py-3.5 border-b border-[#b040d8]/7">
                      <span className="font-sans text-[9px] font-bold tracking-[1px] uppercase bg-[#f0a800]/15 text-[#f0a800] px-2 py-[3px]">YOU</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
