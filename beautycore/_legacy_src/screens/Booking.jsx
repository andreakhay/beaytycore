import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const SERVICES = ['Japanese Head Spa','Hair Design','Face & Laser','Nail Studio','Massage Therapy']
const PRICES   = ['Mula ₱850','Mula ₱180','Mula ₱600','Mula ₱180','Mula ₱350']
const TIMES    = ['9:00 AM','10:00 AM','11:00 AM','1:00 PM','2:00 PM','3:00 PM','4:00 PM','5:00 PM']

export default function Booking() {
  const [step, setStep] = useState(1)
  const [service, setService] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [notes, setNotes] = useState('')
  const [done, setDone] = useState(false)
  const navigate = useNavigate()

  const inputCls = "w-full bg-[#b040d8]/8 border border-[#b040d8]/25 text-white font-sans text-xs px-3.5 py-3 outline-none transition-colors focus:border-[#f0a800]"
  const labelCls = "block font-sans text-[10px] font-semibold tracking-[1.5px] uppercase text-[#c8a8e0] mb-[7px]"
  const btnGold  = "flex-1 bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[2.5px] uppercase py-3.5 border-none cursor-pointer transition-all duration-200 hover:bg-[#f5c040]"
  const btnOut   = "flex-1 bg-transparent text-[#f0a800] border border-[#f0a800] font-sans text-[11px] font-bold tracking-[2.5px] uppercase py-[13px] cursor-pointer transition-all duration-200 hover:bg-[#f0a800]/10"

  const StepDot = ({ n }) => (
    <div className={`flex items-center gap-2 font-sans text-[11px] font-semibold tracking-[1px] uppercase transition-colors duration-200 ${step === n ? 'text-[#f0a800]' : 'text-[#6a4a88]'}`}>
      <span className={`w-[26px] h-[26px] rounded-full border flex items-center justify-center text-[11px] transition-all duration-200 ${step === n ? 'border-[#f0a800] bg-[#f0a800] text-[#1a0a2e]' : 'border-[#6a4a88]'}`}>{n}</span>
      {['Service','Schedule','Confirm'][n-1]}
    </div>
  )

  if (done) return (
    <div className="min-h-screen flex items-center justify-center px-6" style={{ background: 'linear-gradient(135deg,#1a0a2e 0%,#2d1054 60%,#1a0a2e 100%)' }}>
      <div className="w-full max-w-[620px] flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-1">
          <span className="font-serif text-[18px] font-semibold tracking-[3px] text-white">ANDREA'S</span>
          <span className="font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">AESTHETIC &amp; WELLNESS CLINIC</span>
        </div>
        <div className="w-full bg-white/[0.04] border border-[#b040d8]/25 px-9 py-10 text-center backdrop-blur-md">
          <div className="w-[60px] h-[60px] rounded-full bg-[#f0a800]/15 border-2 border-[#f0a800] text-[#f0a800] text-[24px] flex items-center justify-center mx-auto mb-5">✓</div>
          <h3 className="font-serif text-[20px] font-normal text-white mb-3 tracking-[1px]">Booking Submitted!</h3>
          <p className="font-sans text-[11px] text-[#c8a8e0] mb-6">Thank you. We'll confirm your appointment shortly.</p>
          <Link to="/" className="block w-full bg-[#f0a800] text-[#1a0a2e] font-sans text-[11px] font-bold tracking-[2.5px] uppercase py-3.5 text-center hover:bg-[#f5c040] transition-colors">BACK TO HOME</Link>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-8" style={{ background: 'linear-gradient(135deg,#1a0a2e 0%,#2d1054 60%,#1a0a2e 100%)' }}>
      <div className="w-full max-w-[620px] flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-1">
          <span className="font-serif text-[18px] font-semibold tracking-[3px] text-white">ANDREA'S</span>
          <span className="font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">AESTHETIC &amp; WELLNESS CLINIC</span>
        </div>

        <div className="w-full bg-white/[0.04] border border-[#b040d8]/25 px-9 py-10 backdrop-blur-md">
          <h2 className="font-serif text-[28px] font-normal text-white text-center mb-1.5">Book an Appointment</h2>
          <p className="font-sans text-[11px] text-[#c8a8e0] text-center mb-8">Choose your service and preferred schedule</p>

          {/* Steps */}
          <div className="flex items-center mb-8">
            <StepDot n={1} />
            <div className="flex-1 h-px bg-[#b040d8]/20 mx-3" />
            <StepDot n={2} />
            <div className="flex-1 h-px bg-[#b040d8]/20 mx-3" />
            <StepDot n={3} />
          </div>

          {/* Step 1 */}
          {step === 1 && (
            <div>
              <h3 className="font-serif text-[20px] font-normal text-white mb-5 tracking-[1px]">Select a Service</h3>
              <div className="grid grid-cols-2 gap-3 mb-6 max-[480px]:grid-cols-1">
                {SERVICES.map((s, i) => (
                  <label key={s} className="cursor-pointer">
                    <input type="radio" name="service" value={s} checked={service === s} onChange={() => setService(s)} className="hidden" />
                    <div className={`border p-4 transition-all duration-200 ${service === s ? 'border-[#f0a800] bg-[#f0a800]/8' : 'border-[#b040d8]/25 bg-[#b040d8]/5 hover:border-[#f0a800]/50'}`}>
                      <p className="font-sans text-xs font-semibold text-white mb-1">{s}</p>
                      <p className="font-sans text-[11px] text-[#f0a800]">{PRICES[i]}</p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex gap-3 mt-6">
                <button className={btnGold} onClick={() => setStep(2)}>NEXT</button>
              </div>
            </div>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <div>
              <h3 className="font-serif text-[20px] font-normal text-white mb-5 tracking-[1px]">Choose Date &amp; Time</h3>
              <div className="mb-4"><label className={labelCls}>Preferred Date</label><input type="date" value={date} onChange={e => setDate(e.target.value)} className={inputCls} /></div>
              <div className="mb-4">
                <label className={labelCls}>Preferred Time</label>
                <select value={time} onChange={e => setTime(e.target.value)} className={inputCls + ' [&>option]:bg-[#2d1054]'}>
                  <option value="">Select a time slot</option>
                  {TIMES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div className="mb-4">
                <label className={labelCls}>Special Requests (optional)</label>
                <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Any notes for your therapist..." className={inputCls + ' resize-none'} />
              </div>
              <div className="flex gap-3 mt-6">
                <button className={btnOut} onClick={() => setStep(1)}>BACK</button>
                <button className={btnGold} onClick={() => setStep(3)}>NEXT</button>
              </div>
            </div>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <div>
              <h3 className="font-serif text-[20px] font-normal text-white mb-5 tracking-[1px]">Confirm Booking</h3>
              <div className="border border-[#b040d8]/20 bg-[#b040d8]/5 p-5 mb-4">
                {[['Service', service || '—'], ['Date', date || '—'], ['Time', time || '—']].map(([k, v]) => (
                  <div key={k} className="flex justify-between items-center py-2.5 border-b border-white/5 text-xs last:border-b-0">
                    <span className="text-[#9a7ab8]">{k}</span>
                    <strong className="text-white">{v}</strong>
                  </div>
                ))}
                <div className="flex justify-between items-center py-2.5 text-xs">
                  <span className="text-[#9a7ab8]">Status</span>
                  <span className="font-sans text-[10px] font-bold tracking-[1px] bg-[#f0a800]/15 text-[#f0a800] px-2.5 py-[3px]">Pending Confirmation</span>
                </div>
              </div>
              <p className="font-sans text-[11px] text-[#9a7ab8] leading-[1.7] mb-2">You will receive a confirmation via email once our team reviews your booking.</p>
              <div className="flex gap-3 mt-6">
                <button className={btnOut} onClick={() => setStep(2)}>BACK</button>
                <button className={btnGold} onClick={() => setDone(true)}>CONFIRM BOOKING</button>
              </div>
            </div>
          )}
        </div>

        <Link to="/" className="font-sans text-[11px] text-[#9a7ab8] tracking-[1px] hover:text-[#f0a800] transition-colors">← Back to website</Link>
      </div>
    </div>
  )
}
