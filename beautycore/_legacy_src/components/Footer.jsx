import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="bg-gradient-to-b from-[#1a0a2e] to-[#0d0520] pt-[60px] px-10 border-t border-[#b040d8]/15">
      {/* Logo */}
      <div className="flex flex-col items-center mb-12">
        <span className="font-serif text-lg font-semibold tracking-[3px] text-white">ANDREA'S</span>
        <span className="font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">AESTHETIC &amp; WELLNESS CLINIC</span>
      </div>

      {/* Columns */}
      <div className="grid grid-cols-3 gap-10 max-w-[900px] mx-auto mb-12 text-center max-[900px]:grid-cols-1 max-[900px]:text-left max-[900px]:gap-7">
        <div>
          <h4 className="font-sans text-[10px] font-semibold tracking-[2.5px] text-[#f0a800] mb-[14px] uppercase">LOCATION</h4>
          <p className="font-sans text-xs text-[#e0c8f0] leading-[1.9]">Purok 5, Bagasbas Road<br />Daet, Camarines Norte 4600<br />Philippines</p>
        </div>
        <div>
          <h4 className="font-sans text-[10px] font-semibold tracking-[2.5px] text-[#f0a800] mb-[14px] uppercase">CONTACT</h4>
          <p className="font-sans text-xs text-[#e0c8f0] leading-[1.9]">andreasaestheticwellness@gmail.com<br />+63 954 123 4567</p>
        </div>
        <div>
          <h4 className="font-sans text-[10px] font-semibold tracking-[2.5px] text-[#f0a800] mb-[14px] uppercase">HOURS</h4>
          <p className="font-sans text-xs text-[#e0c8f0] leading-[1.9]">Mon–Sat: 9AM – 8PM<br />Sunday: 10AM – 6PM</p>
        </div>
      </div>

      {/* Bottom */}
      <div className="border-t border-white/[0.07] py-5 flex justify-between items-center max-w-[1100px] mx-auto max-[900px]:flex-col max-[900px]:gap-3 max-[900px]:text-center">
        <p className="text-[10px] text-[#9a7ab8] tracking-[0.5px]">© 2026 Andrea's Aesthetic &amp; Wellness Clinic. All rights reserved.</p>
        <div className="flex gap-5">
          <Link to="#" className="text-[10px] text-[#9a7ab8] tracking-[0.5px] hover:text-[#f0a800] transition-colors">Privacy Policy</Link>
          <Link to="#" className="text-[10px] text-[#9a7ab8] tracking-[0.5px] hover:text-[#f0a800] transition-colors">Contact</Link>
          <Link to="#" className="text-[10px] text-[#9a7ab8] tracking-[0.5px] hover:text-[#f0a800] transition-colors">Legal</Link>
        </div>
      </div>
    </footer>
  )
}
