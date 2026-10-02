import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  const links = [
    { to: '/', label: 'Home' },
    { to: '/services', label: 'Services' },
    { to: '/about', label: 'About' },
    { to: '/contact', label: 'Contact' },
  ]

  return (
    <nav className="sticky top-0 z-[1000] flex flex-wrap items-center justify-between px-10 py-4 bg-[#1a0a2e] border-b border-[#b040d8]/20">
      {/* Logo */}
      <div className="flex flex-col leading-tight">
        <span className="font-serif text-lg font-semibold tracking-[3px] text-white">ANDREA'S</span>
        <span className="font-sans text-[8px] tracking-[2px] text-[#f0a800] uppercase">AESTHETIC &amp; WELLNESS CLINIC</span>
      </div>

      {/* Hamburger */}
      <button
        className="hidden max-[900px]:flex flex-col gap-[5px] p-1 bg-transparent border-none cursor-pointer"
        onClick={() => setOpen(o => !o)}
        aria-label="Toggle menu"
      >
        <span className="block w-[22px] h-[2px] bg-white" />
        <span className="block w-[22px] h-[2px] bg-white" />
        <span className="block w-[22px] h-[2px] bg-white" />
      </button>

      {/* Links */}
      <ul className={`flex gap-[26px] items-center max-[900px]:flex-col max-[900px]:w-full max-[900px]:gap-0 max-[900px]:bg-[#1a0a2e] max-[900px]:py-3 ${open ? 'max-[900px]:flex' : 'max-[900px]:hidden'}`}>
        {links.map(l => (
          <li key={l.label}>
            <Link
              to={l.to}
              className={`font-sans text-[11px] font-medium tracking-[1.5px] uppercase transition-colors duration-200 max-[900px]:block max-[900px]:py-[10px] max-[900px]:border-b max-[900px]:border-white/5 ${pathname === l.to ? 'text-[#f0a800]' : 'text-[#e0c8f0] hover:text-[#f0a800]'}`}
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>

      {/* Book Now */}
      <Link
        to="/login"
        className="font-sans text-[10px] font-semibold tracking-[2px] uppercase text-[#f0a800] border border-[#f0a800] px-[18px] py-2 transition-all duration-200 hover:bg-[#f0a800] hover:text-[#1a0a2e] max-[900px]:hidden"
      >
        BOOK NOW
      </Link>
    </nav>
  )
}
