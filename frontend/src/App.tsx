import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import Router from './routes/Router'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Router />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
