import { useState } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function Contact() {
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({ first: '', last: '', email: '', message: '' })

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitted(true)
    setTimeout(() => setSubmitted(false), 3000)
    setForm({ first: '', last: '', email: '', message: '' })
  }

  return (
    <div>
      <Navbar />

      {/* HERO */}
      <section className="px-10 pt-20 pb-[60px]" style={{ background: 'linear-gradient(160deg,#1a0a2e 0%,#2d1054 100%)' }}>
        <div className="max-w-[1100px] mx-auto">
          <h1 className="font-serif font-light text-white mb-4" style={{ fontSize: 'clamp(36px,6vw,60px)' }}>Contact Us</h1>
          <p className="font-sans text-[13px] text-[#e0c8f0] max-w-[520px] leading-[1.8]">
            We'd love to hear from you. Reach out to schedule an appointment, ask a question, or simply learn more about what we offer.
          </p>
        </div>
      </section>

      {/* BODY */}
      <section className="px-10 py-[60px] pb-20" style={{ background: 'linear-gradient(180deg,#1a0a2e 0%,#0f0525 100%)' }}>
        <div className="max-w-[1100px] mx-auto grid grid-cols-[1fr_1.2fr] gap-[60px] items-start max-[900px]:grid-cols-1">

          {/* Info */}
          <div>
            <h3 className="font-sans text-[11px] font-semibold tracking-[3px] text-[#f0a800] uppercase mb-8">GET IN TOUCH</h3>
            {[
              { icon: 'LOC', title: 'ADDRESS', lines: ['Purok 5, Bagasbas Road', 'Daet, Camarines Norte 4600', 'Philippines'] },
              { icon: 'TEL', title: 'PHONE', lines: ['+63 954 123 4567', '+63 954 765 4321'] },
              { icon: 'MSG', title: 'EMAIL', lines: ['andreasaestheticwellness@gmail.com'] },
              { icon: 'HRS', title: 'HOURS', lines: ['Monday–Saturday: 9AM – 8PM', 'Sunday: Closed'] },
            ].map(({ icon, title, lines }) => (
              <div key={title} className="flex gap-4 mb-7 items-start">
                <div className="w-9 h-9 shrink-0 mt-0.5 flex items-center justify-center border border-[#f0a800]/20 bg-[#f0a800]/8 font-sans text-[9px] font-bold tracking-[1px] text-[#f0a800]">{icon}</div>
                <div>
                  <h5 className="font-sans text-[10px] font-semibold tracking-[2px] text-[#f0a800] uppercase mb-1.5">{title}</h5>
                  {lines.map(l => <p key={l} className="font-sans text-xs text-[#e0c8f0] leading-[1.8]">{l}</p>)}
                </div>
              </div>
            ))}
            <div className="mt-9 pt-7 border-t border-[#b040d8]/20">
              <h5 className="font-sans text-[10px] font-semibold tracking-[2px] text-[#f0a800] uppercase mb-2.5">STAY CONNECTED</h5>
              <p className="font-sans text-xs text-[#e0c8f0] leading-[1.8] mb-3">Follow us on social media for the latest updates, promotions, and wellness tips from our team.</p>
              <Link to="#" className="font-sans text-[11px] font-medium tracking-[1px] text-[#f0a800] hover:text-[#f5c040] transition-colors">→ FOLLOW US ON INSTAGRAM</Link>
            </div>
          </div>

          {/* Form */}
          <div>
            <h3 className="font-serif text-[24px] font-normal text-white mb-7">Send an Inquiry</h3>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
              <div className="grid grid-cols-2 gap-4 max-[600px]:grid-cols-1">
                <input value={form.first} onChange={e => setForm(f => ({ ...f, first: e.target.value }))} type="text" placeholder="FIRST NAME" required
                  className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] tracking-[1px] px-4 py-3.5 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/30" />
                <input value={form.last} onChange={e => setForm(f => ({ ...f, last: e.target.value }))} type="text" placeholder="LAST NAME" required
                  className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] tracking-[1px] px-4 py-3.5 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/30" />
              </div>
              <input value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} type="email" placeholder="EMAIL ADDRESS" required
                className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] tracking-[1px] px-4 py-3.5 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/30" />
              <textarea value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} rows={5} placeholder="YOUR MESSAGE HERE..."
                className="w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-[11px] tracking-[1px] px-4 py-3.5 outline-none transition-colors focus:border-[#f0a800] placeholder:text-white/30 resize-none" />
              <button type="submit"
                className={`w-full font-sans text-[11px] font-bold tracking-[2.5px] uppercase py-4 border-none cursor-pointer transition-all duration-200 ${submitted ? 'bg-[#7b2fa0] text-white' : 'bg-[#f0a800] text-[#1a0a2e] hover:bg-[#f5c040]'}`}>
                {submitted ? 'MESSAGE SENT' : 'SUBMIT INQUIRY'}
              </button>
            </form>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
