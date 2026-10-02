import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [role, setRole] = useState('client')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, loginError } = useAuth()
  const navigate = useNavigate()

  function handleSubmit(e) {
    e.preventDefault()
    const result = login(email, password, role)
    if (result.success) {
      if (result.role === 'admin') navigate('/admin/dashboard')
      else if (result.role === 'stylist') navigate('/stylist/dashboard')
      else navigate('/client/dashboard')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-8"
      style={{ background: 'linear-gradient(135deg,#1a0a2e 0%,#2d1054 60%,#1a0a2e 100%)' }}>
      <div className="w-full max-w-[460px] flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-1">
          <span className="font-serif text-[18px] font-semibold tracking-[3px] text-white">ANDREA'S</span>
          <span className="font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">AESTHETIC &amp; WELLNESS CLINIC</span>
        </div>

        <div className="w-full bg-white/[0.04] border border-[#b040d8]/25 px-9 py-10 backdrop-blur-md">
          <h2 className="font-serif text-[28px] font-normal text-white text-center mb-1.5">Welcome Back</h2>
          <p className="font-sans text-[11px] text-[#c8a8e0] text-center tracking-[0.5px] mb-7">Sign in to your account to continue</p>

          {/* Demo credentials hint */}
          <div className="bg-[#f0a800]/8 border border-[#f0a800]/20 p-3 mb-5 text-[10px] text-[#c8a8e0] leading-[1.8]">
            <p className="text-[#f0a800] font-bold mb-1 tracking-[1px] uppercase">Demo Credentials</p>
            <p>Admin: admin@andreas.com / admin123</p>
            <p>Client: maria@email.com / client123</p>
            <p>Stylist: lara@andreas.com / stylist123</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="flex border border-[#b040d8]/30 mb-6">
              {['client','admin','stylist'].map(r => (
                <button key={r} type="button" onClick={() => setRole(r)}
                  className={`flex-1 py-2.5 font-sans text-[11px] font-semibold tracking-[1.5px] uppercase cursor-pointer border-none transition-all duration-200
                    ${role === r ? 'bg-[#7b2fa0] text-white' : 'bg-transparent text-[#9a7ab8]'}`}>
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </button>
              ))}
            </div>

            {loginError && (
              <div className="bg-[#eb5757]/10 border border-[#eb5757]/30 text-[#eb5757] text-[11px] px-3 py-2 mb-4">{loginError}</div>
            )}

            <div className="mb-4">
              <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Email Address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required
                className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/25" />
            </div>
            <div className="mb-5">
              <label className="block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]">Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required
                className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/25" />
            </div>

            <div className="flex justify-between items-center mb-5 text-[11px]">
              <label className="flex items-center gap-[7px] text-[#c8a8e0] cursor-pointer">
                <input type="checkbox" className="accent-[#7b2fa0]" /> Remember me
              </label>
              <Link to="#" className="text-[#f0a800] hover:text-[#f5c040] transition-colors">Forgot password?</Link>
            </div>

            <button type="submit"
              className="block w-full bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[2.5px] uppercase py-3.5 border-none cursor-pointer transition-all duration-200 hover:bg-[#f5c040]">
              SIGN IN
            </button>
            <p className="text-center font-sans text-[11px] text-[#9a7ab8] mt-[18px]">
              Don't have an account? <Link to="/register" className="text-[#f0a800]">Create one</Link>
            </p>
          </form>
        </div>
        <Link to="/" className="font-sans text-[11px] text-[#9a7ab8] tracking-[1px] hover:text-[#f0a800] transition-colors">← Back to website</Link>
      </div>
    </div>
  )
}
