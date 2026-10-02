import { useState } from 'react'
import AdminSidebar from '../../components/AdminSidebar'
import { useAuth } from '../../context/AuthContext'

const ROLES = {
  admin:  { label:'Administrator', color:'text-[#f0a800]', bg:'bg-[#f0a800]/15', perms:['All Access','User Management','Financial Reports','Inventory','Appointments','Security Logs'] },
  client: { label:'Client', color:'text-[#6fcf97]', bg:'bg-[#6fcf97]/15', perms:['View Own Appointments','Book Services','Update Profile','AI Advisor','Nail & Hair Studio'] },
}

const PERMISSIONS = [
  { module:'Appointments', admin:true, client:true },
  { module:'Client Management (CRM)', admin:true, client:false },
  { module:'Inventory Management', admin:true, client:false },
  { module:'Financial Reports', admin:true, client:false },
  { module:'Market Trends', admin:true, client:false },
  { module:'Security & Access Logs', admin:true, client:false },
  { module:'AI Style Advisor', admin:true, client:true },
  { module:'Nail Studio', admin:true, client:true },
  { module:'Hair Studio', admin:true, client:true },
  { module:'Profile Management', admin:true, client:true },
  { module:'User Management', admin:true, client:false },
]

export default function AdminSecurity() {
  const { activityLog, USERS } = useAuth()
  const [activeTab, setActiveTab] = useState('logs')
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  const filteredLogs = activityLog.filter(l => {
    const matchSearch = l.user.toLowerCase().includes(search.toLowerCase()) || l.action.toLowerCase().includes(search.toLowerCase())
    const matchStatus = !filterStatus || l.status === filterStatus
    return matchSearch && matchStatus
  })

  const failedAttempts = activityLog.filter(l => l.status === 'failed').length
  const activeUsers = [...new Set(activityLog.filter(l => l.status === 'success').map(l => l.user))].length

  const thCls = "text-left font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] px-4 py-2.5 border-b border-[#b040d8]/15"
  const tdCls = "px-4 py-3 text-[#e0c8f0] border-b border-[#b040d8]/7 align-middle text-xs"

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <AdminSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">Security &amp; Access Control</h1>
            <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1px]">User management · Role permissions · Activity logs</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#6fcf97]" />
            <span className="font-sans text-[10px] text-[#6fcf97] tracking-[1px]">SYSTEM SECURE</span>
          </div>
        </header>

        <div className="p-8 flex-1">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-5 mb-8 max-[1024px]:grid-cols-2">
            {[
              { label:'Total Users', value: USERS.length, color:'text-white' },
              { label:'Active Sessions', value: activeUsers, color:'text-[#6fcf97]' },
              { label:'Failed Login Attempts', value: failedAttempts, color:'text-[#eb5757]' },
              { label:'Security Status', value:'Secure', color:'text-[#6fcf97]' },
            ].map(s => (
              <div key={s.label} className="relative bg-[#1a0a2e] border border-[#b040d8]/15 px-6 py-[22px] overflow-hidden stat-card-accent">
                <p className="font-sans text-[9px] font-bold tracking-[2px] uppercase text-[#9a7ab8] mb-2.5">{s.label}</p>
                <p className={`font-serif text-[30px] font-normal leading-none ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="flex border-b border-[#b040d8]/15 mb-6">
            {[['logs','Activity Logs'],['users','User Management'],['roles','Role Permissions']].map(([t,l]) => (
              <button key={t} onClick={() => setActiveTab(t)}
                className={`font-sans text-[11px] font-semibold tracking-[1.5px] uppercase px-5 py-2.5 border-b-2 -mb-px cursor-pointer bg-none border-none transition-all duration-200 ${activeTab===t?'text-[#f0a800] border-b-[#f0a800]':'text-[#9a7ab8] border-b-transparent hover:text-white'}`}>
                {l}
              </button>
            ))}
          </div>

          {/* ACTIVITY LOGS */}
          {activeTab === 'logs' && (
            <div>
              <div className="flex gap-3 mb-5 flex-wrap">
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search user or action..."
                  className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] min-w-[220px] placeholder:text-white/25" />
                <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                  className="bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] px-3.5 py-[9px] outline-none focus:border-[#f0a800] [&>option]:bg-[#2d1054]">
                  <option value="">All Status</option>
                  <option value="success">Success</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr>{['#','User','Action','Timestamp','IP Address','Status'].map(h => <th key={h} className={thCls}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {filteredLogs.length === 0
                      ? <tr><td colSpan={6} className="text-center text-[#6a4a88] py-8 text-xs">No logs found.</td></tr>
                      : filteredLogs.map((l, i) => (
                        <tr key={l.id} className="hover:bg-[#b040d8]/5 transition-colors">
                          <td className={tdCls + ' text-[#6a4a88]'}>{i+1}</td>
                          <td className={tdCls + ' font-semibold text-white'}>{l.user}</td>
                          <td className={tdCls}>{l.action}</td>
                          <td className={tdCls + ' text-[#9a7ab8]'}>{l.time}</td>
                          <td className={tdCls + ' font-mono text-[10px]'}>{l.ip}</td>
                          <td className={tdCls}>
                            <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${l.status === 'success' ? 'bg-[#6fcf97]/15 text-[#6fcf97]' : 'bg-[#eb5757]/15 text-[#eb5757]'}`}>
                              {l.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    }
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* USER MANAGEMENT */}
          {activeTab === 'users' && (
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15 overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>{['ID','Name','Email','Role','Status','Actions'].map(h => <th key={h} className={thCls}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {USERS.map(u => (
                    <tr key={u.id} className="hover:bg-[#b040d8]/5 transition-colors">
                      <td className={tdCls + ' text-[#6a4a88]'}>#{u.id}</td>
                      <td className={tdCls}>
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#f0a800] flex items-center justify-center text-[11px] font-bold text-white shrink-0">{u.avatar}</div>
                          <span className="font-semibold text-white">{u.name}</span>
                        </div>
                      </td>
                      <td className={tdCls}>{u.email}</td>
                      <td className={tdCls}>
                        <span className={`inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] ${ROLES[u.role].bg} ${ROLES[u.role].color}`}>
                          {ROLES[u.role].label}
                        </span>
                      </td>
                      <td className={tdCls}>
                        <span className="inline-block font-sans text-[9px] font-bold tracking-[1px] uppercase px-2.5 py-[3px] bg-[#6fcf97]/15 text-[#6fcf97]">Active</span>
                      </td>
                      <td className={tdCls}>
                        <div className="flex gap-1.5">
                          <button className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase border border-[#b040d8]/40 text-[#c8a8e0] px-3 py-1.5 cursor-pointer bg-transparent hover:border-[#f0a800] hover:text-[#f0a800] transition-all">Edit</button>
                          {u.role !== 'admin' && <button className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#eb5757]/15 text-[#eb5757] border border-[#eb5757]/30 px-3 py-1.5 cursor-pointer hover:bg-[#eb5757]/25 transition-colors">Suspend</button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ROLE PERMISSIONS */}
          {activeTab === 'roles' && (
            <div>
              {/* Role cards */}
              <div className="grid grid-cols-2 gap-5 mb-6">
                {Object.entries(ROLES).map(([key, role]) => (
                  <div key={key} className="bg-[#1a0a2e] border border-[#b040d8]/15 p-5">
                    <div className="flex items-center gap-3 mb-4">
                      <span className={`inline-block font-sans text-[10px] font-bold tracking-[1px] uppercase px-3 py-1.5 ${role.bg} ${role.color}`}>{role.label}</span>
                    </div>
                    <p className="font-sans text-[10px] text-[#9a7ab8] uppercase tracking-[1.5px] mb-3">Permissions</p>
                    <div className="flex flex-col gap-2">
                      {role.perms.map(p => (
                        <div key={p} className="flex items-center gap-2">
                          <span className="text-[#6fcf97] text-[12px]">✓</span>
                          <span className="font-sans text-[11px] text-[#e0c8f0]">{p}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Permission matrix */}
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                  <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Permission Matrix</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr>
                        <th className={thCls}>Module</th>
                        <th className={thCls + ' text-center'}>Administrator</th>
                        <th className={thCls + ' text-center'}>Client</th>
                      </tr>
                    </thead>
                    <tbody>
                      {PERMISSIONS.map(p => (
                        <tr key={p.module} className="hover:bg-[#b040d8]/5 transition-colors">
                          <td className={tdCls + ' font-medium text-white'}>{p.module}</td>
                          <td className={tdCls + ' text-center'}>
                            {p.admin ? <span className="text-[#6fcf97] text-[16px]">✓</span> : <span className="text-[#eb5757] text-[16px]">✗</span>}
                          </td>
                          <td className={tdCls + ' text-center'}>
                            {p.client ? <span className="text-[#6fcf97] text-[16px]">✓</span> : <span className="text-[#eb5757] text-[16px]">✗</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
