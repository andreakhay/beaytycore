import { Link } from 'react-router-dom'
import AdminSidebar from '../../components/AdminSidebar'

const todayAppts = [
  { client:'Maria Santos', service:'Nail Studio', time:'9:00 AM', status:'Confirmed' },
  { client:'Jessa Reyes', service:'Japanese Head Spa', time:'10:00 AM', status:'Confirmed' },
  { client:'Carla Dizon', service:'Hair Design', time:'11:30 AM', status:'Pending' },
  { client:'Ana Lim', service:'Massage Therapy', time:'1:00 PM', status:'Confirmed' },
  { client:'Rose Tan', service:'Face & Laser', time:'3:00 PM', status:'Pending' },
]
const revenue = [
  { name:'Nail Studio', amount:'₱4,300', pct:72 },
  { name:'Hair Design', amount:'₱3,800', pct:60 },
  { name:'Face & Laser', amount:'₱3,200', pct:53 },
  { name:'Massage Therapy', amount:'₱2,600', pct:37 },
  { name:'Japanese Head Spa', amount:'₱1,700', pct:22 },
]
const lowStock = [
  { name:'OPI Gel Polish – Nude', cat:'Nail', stock:'3 pcs', min:'10 pcs' },
  { name:'Keratin Treatment 500ml', cat:'Hair', stock:'1 btl', min:'5 btl' },
  { name:'Hyaluronic Serum 30ml', cat:'Facial', stock:'2 pcs', min:'8 pcs' },
  { name:'Massage Oil – Lavender', cat:'Massage', stock:'4 btl', min:'10 btl' },
  { name:'Nail Primer', cat:'Nail', stock:'2 pcs', min:'6 pcs' },
]

const Badge = ({ status }) => {
  const map = { Confirmed:'bg-[#6fcf97]/15 text-[#6fcf97]', Pending:'bg-[#f0a800]/15 text-[#f0a800]', Completed:'bg-[#7b2fa0]/25 text-[#d060f0]', Cancelled:'bg-[#eb5757]/15 text-[#eb5757]', 'Low Stock':'bg-[#eb5757]/15 text-[#eb5757]' }
  return <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${map[status] || ''}`}>{status}</span>
}

export default function AdminDashboard() {
  const today = new Date().toLocaleDateString('en-PH', { weekday:'long', year:'numeric', month:'long', day:'numeric' })
  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        {/* Topbar */}
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-[11px] text-[#9a7ab8]">{today}</span>
            <Link to="/admin/appointments" className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 hover:bg-[#f5c040] transition-colors">+ New Appointment</Link>
          </div>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-8 max-[1024px]:grid-cols-2">
            {[
              { label:"Today's Appointments", value:'8', change:'+ 2 from yesterday', up:true },
              { label:'Total Clients', value:'247', change:'+ 12 this month', up:true },
              { label:'Revenue This Month', value:'₱18.5k', change:'+ 6.2% vs last month', up:true },
              { label:'Low Stock Items', value:'5', change:'Needs reorder', up:false },
            ].map(({ label, value, change, up }) => (
              <div key={label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{label}</p>
                <p className="font-serif text-[34px] font-normal text-white leading-none mb-1.5">{value}</p>
                <p className={`text-[10px] ${up ? 'text-[#6fcf97]' : 'text-[#eb5757]'}`}>{change}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 mb-6" style={{ gridTemplateColumns:'1.4fr 1fr' }}>
            {/* Today's appts */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center justify-between">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Today's Appointments</h2>
                <Link to="/admin/appointments" className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 hover:border-[#f0a800] hover:text-[#f0a800] transition-all">View All</Link>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead><tr>{['Client','Service','Time','Status'].map(h => <th key={h} className="text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15">{h}</th>)}</tr></thead>
                <tbody>
                  {todayAppts.map(a => (
                    <tr key={a.client} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{a.client}</td>
                      <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{a.service}</td>
                      <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{a.time}</td>
                      <td className="px-3.5 py-3 border-b border-[#b040d8]/7"><Badge status={a.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Revenue */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
              <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Revenue by Service</h2>
              </div>
              <div className="p-6 flex flex-col gap-4">
                {revenue.map(r => (
                  <div key={r.name}>
                    <div className="flex justify-between font-sans text-[11px] text-[#e0c8f0] mb-1">
                      <span>{r.name}</span><span className="text-[#f0a800]">{r.amount}</span>
                    </div>
                    <div className="bg-[#b040d8]/10 h-1.5 w-full">
                      <div className="progress-bar-fill h-full" style={{ width:`${r.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Low stock */}
          <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
            <div className="px-6 py-[18px] border-b border-[#b040d8]/12 flex items-center justify-between">
              <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Low Stock Alerts</h2>
              <Link to="/admin/inventory" className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3.5 py-1.5 hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Manage Inventory</Link>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead><tr>{['Product','Category','Stock','Min Level','Status'].map(h => <th key={h} className="text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-3.5 py-2.5 border-b border-[#b040d8]/15">{h}</th>)}</tr></thead>
              <tbody>
                {lowStock.map(i => (
                  <tr key={i.name} className="hover:bg-[#b040d8]/5 transition-colors">
                    <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{i.name}</td>
                    <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{i.cat}</td>
                    <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{i.stock}</td>
                    <td className="px-3.5 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7">{i.min}</td>
                    <td className="px-3.5 py-3 border-b border-[#b040d8]/7"><Badge status="Low Stock" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
