import { useState } from 'react'
import ClientSidebar from '../../components/ClientSidebar'

export default function ClientProfile() {
  const [profile, setProfile] = useState({ first:'Maria', last:'Santos', email:'maria@email.com', phone:'+63 912 111 1111', birthday:'1995-03-12', contact:'Email', address:'' })
  const [toast, setToast] = useState('')

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  function saveProfile() {
    showToast('Profile updated!')
  }

  const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-[11px] outline-none transition-colors focus:border-[#f0a800] [&>option]:bg-[#2d1054] placeholder:text-white/25"
  const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"

  return (
    <div className="flex min-h-screen bg-[#0f0520] font-sans">
      <ClientSidebar />
      <div className="ml-[240px] flex-1 flex flex-col">
        <header className="sticky top-0 z-50 bg-[#1a0a2e] border-b border-[#b040d8]/15 px-8 py-4">
          <h1 className="font-serif text-[22px] font-normal text-white tracking-[1px]">My Profile</h1>
        </header>

        <div className="p-8 flex-1">
          <div className="grid gap-6 items-start" style={{ gridTemplateColumns:'280px 1fr' }}>
            {/* Profile card */}
            <div className="bg-[#1a0a2e] border border-[#b040d8]/15 p-6 text-center">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#7b2fa0] to-[#f0a800] flex items-center justify-center text-[32px] font-bold text-white mx-auto mb-4">
                {profile.first.charAt(0).toUpperCase()}
              </div>
              <p className="font-serif text-[22px] text-white mb-1">{profile.first} {profile.last}</p>
              <p className="font-sans text-[11px] text-[#9a7ab8] mb-5">Client since January 2025</p>
              <div className="flex justify-center gap-6 mb-5">
                <div className="text-center">
                  <p className="font-serif text-[28px] text-[#f0a800]">14</p>
                  <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1px]">VISITS</p>
                </div>
                <div className="text-center">
                  <p className="font-serif text-[28px] text-[#f0a800]">280</p>
                  <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1px]">POINTS</p>
                </div>
              </div>
              <div className="bg-[#f0a800]/7 border border-[#f0a800]/20 p-3 mb-4">
                <p className="font-sans text-[10px] text-[#9a7ab8] tracking-[1.5px] uppercase mb-1">Loyalty Tier</p>
                <p className="text-[#f0a800] font-bold text-[13px] tracking-[1px]">GOLD MEMBER</p>
              </div>
              <p className="font-sans text-[11px] text-[#9a7ab8] leading-[1.7]">Earn 20 points per visit. Redeem 100 points for ₱100 off your next service.</p>
            </div>

            {/* Forms */}
            <div>
              <div className="bg-[#1a0a2e] border border-[#b040d8]/15 mb-6">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                  <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Personal Information</h2>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-2 gap-3.5 mb-4">
                    <div><label className={labelCls}>First Name</label><input value={profile.first} onChange={e=>setProfile(p=>({...p,first:e.target.value}))} className={inputCls} /></div>
                    <div><label className={labelCls}>Last Name</label><input value={profile.last} onChange={e=>setProfile(p=>({...p,last:e.target.value}))} className={inputCls} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3.5 mb-4">
                    <div><label className={labelCls}>Email</label><input type="email" value={profile.email} onChange={e=>setProfile(p=>({...p,email:e.target.value}))} className={inputCls} /></div>
                    <div><label className={labelCls}>Phone</label><input value={profile.phone} onChange={e=>setProfile(p=>({...p,phone:e.target.value}))} className={inputCls} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3.5 mb-4">
                    <div><label className={labelCls}>Birthday</label><input type="date" value={profile.birthday} onChange={e=>setProfile(p=>({...p,birthday:e.target.value}))} className={inputCls} /></div>
                    <div><label className={labelCls}>Preferred Contact</label>
                      <select value={profile.contact} onChange={e=>setProfile(p=>({...p,contact:e.target.value}))} className={inputCls}>
                        <option>Email</option><option>SMS</option><option>Both</option>
                      </select>
                    </div>
                  </div>
                  <div className="mb-4"><label className={labelCls}>Address</label><input value={profile.address} onChange={e=>setProfile(p=>({...p,address:e.target.value}))} placeholder="Your address (optional)" className={inputCls} /></div>
                  <div className="flex justify-end">
                    <button onClick={saveProfile} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Save Changes</button>
                  </div>
                </div>
              </div>

              <div className="bg-[#1a0a2e] border border-[#b040d8]/15">
                <div className="px-6 py-[18px] border-b border-[#b040d8]/12">
                  <h2 className="font-serif text-[18px] font-normal text-white tracking-[1px]">Change Password</h2>
                </div>
                <div className="p-6">
                  <div className="mb-4"><label className={labelCls}>Current Password</label><input type="password" placeholder="••••••••" className={inputCls} /></div>
                  <div className="grid grid-cols-2 gap-3.5 mb-4">
                    <div><label className={labelCls}>New Password</label><input type="password" placeholder="••••••••" className={inputCls} /></div>
                    <div><label className={labelCls}>Confirm New Password</label><input type="password" placeholder="••••••••" className={inputCls} /></div>
                  </div>
                  <div className="flex justify-end">
                    <button onClick={() => showToast('Password updated!')} className="font-sans text-[9px] font-bold tracking-[1.5px] uppercase bg-[#f0a800] text-[#1a0a2e] px-3.5 py-1.5 cursor-pointer border-none hover:bg-[#f5c040] transition-colors">Update Password</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-8 right-8 bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[1.5px] px-6 py-3 z-[9999] transition-opacity duration-300">
          {toast}
        </div>
      )}
    </div>
  )
}
