import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import PoolsPage from './pages/PoolsPage'
import PoolDetailPage from './pages/PoolDetailPage'
import EndpointsPage from './pages/EndpointsPage'
import RepositoryAnalysisPage from './pages/RepositoryAnalysisPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/pools" element={<PoolsPage />} />
        <Route path="/pools/:poolId" element={<PoolDetailPage />} />
        <Route path="/pools/:poolId/analysis" element={<RepositoryAnalysisPage />} />
        <Route path="/endpoints" element={<EndpointsPage />} />
      </Routes>
    </Layout>
  )
}

export default App