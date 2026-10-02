import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

// Demo users for access control
const USERS = [
  { id: 1, name: 'Andrea',       email: 'admin@andreas.com',  password: 'admin123',   role: 'admin',   avatar: 'A' },
  { id: 2, name: 'Maria Santos', email: 'maria@email.com',    password: 'client123',  role: 'client',  avatar: 'M' },
  { id: 3, name: 'Jessa Reyes',  email: 'jessa@email.com',    password: 'client123',  role: 'client',  avatar: 'J' },
  { id: 4, name: 'Lara Cruz',    email: 'lara@andreas.com',   password: 'stylist123', role: 'stylist', avatar: 'L' },
]

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loginError, setLoginError] = useState('')
  const [activityLog, setActivityLog] = useState([
    { id:1, user:'Andrea', action:'Logged in', time:'2026-05-07 08:00', ip:'192.168.1.1', status:'success' },
    { id:2, user:'Maria Santos', action:'Booked appointment', time:'2026-05-07 09:15', ip:'192.168.1.5', status:'success' },
    { id:3, user:'Unknown', action:'Failed login attempt', time:'2026-05-07 10:02', ip:'203.45.67.89', status:'failed' },
    { id:4, user:'Jessa Reyes', action:'Updated profile', time:'2026-05-07 11:30', ip:'192.168.1.8', status:'success' },
    { id:5, user:'Andrea', action:'Exported financial report', time:'2026-05-07 13:00', ip:'192.168.1.1', status:'success' },
    { id:6, user:'Unknown', action:'Failed login attempt', time:'2026-05-07 14:22', ip:'198.51.100.42', status:'failed' },
  ])

  function login(email, password, role) {
    setLoginError('')
    const found = USERS.find(u =>
      u.email.toLowerCase() === email.toLowerCase() &&
      u.password === password
    )
    if (found) {
      setUser(found)
      addLog(found.name, 'Logged in', 'success')
      return { success: true, role: found.role }
    } else {
      setLoginError('Invalid email or password.')
      addLog('Unknown', 'Failed login attempt', 'failed')
      return { success: false }
    }
  }

  function logout() {
    if (user) addLog(user.name, 'Logged out', 'success')
    setUser(null)
  }

  function addLog(userName, action, status) {
    const now = new Date()
    const time = now.toISOString().slice(0,16).replace('T',' ')
    setActivityLog(prev => [
      { id: Date.now(), user: userName, action, time, ip: '192.168.1.x', status },
      ...prev
    ])
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loginError, activityLog, addLog, USERS }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
