import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  CircleStackIcon, 
  ComputerDesktopIcon,
  ChartBarIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { poolsApi, endpointsApi } from '../services/api'

function StatusCard({ title, value, icon: Icon, color = 'primary', subtitle }) {
  const colorClasses = {
    primary: 'bg-primary-50 text-primary-600',
    success: 'bg-success-50 text-success-600',
    warning: 'bg-warning-50 text-warning-600',
    danger: 'bg-danger-50 text-danger-600'
  }

  return (
    <div className="card p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  )
}

function PoolStatusCard({ pool }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success'
      case 'warning': return 'warning'
      case 'critical': return 'danger'
      default: return 'primary'
    }
  }

  const getStatusText = (pool) => {
    if (pool.sync_percentage === 100) return 'All in sync'
    if (pool.sync_percentage >= 80) return 'Mostly synced'
    if (pool.sync_percentage >= 50) return 'Partially synced'
    return 'Needs attention'
  }

  return (
    <Link to={`/pools/${pool.pool_id}`} className="block">
      <div className="card p-4 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{pool.pool_name}</h3>
            <p className="text-sm text-gray-500">{pool.total_endpoints} endpoints</p>
          </div>
          <div className="text-right">
            <div className={`status-badge status-${getStatusColor(pool.overall_status)}`}>
              {getStatusText(pool)}
            </div>
            <p className="text-sm text-gray-500 mt-1">{pool.sync_percentage}% synced</p>
          </div>
        </div>
        
        <div className="mt-4 grid grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-lg font-semibold text-success-600">{pool.in_sync_count}</p>
            <p className="text-xs text-gray-500">In Sync</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-warning-600">{pool.ahead_count}</p>
            <p className="text-xs text-gray-500">Ahead</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-danger-600">{pool.behind_count}</p>
            <p className="text-xs text-gray-500">Behind</p>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-600">{pool.offline_count}</p>
            <p className="text-xs text-gray-500">Offline</p>
          </div>
        </div>
      </div>
    </Link>
  )
}

function Dashboard() {
  const [poolStatuses, setPoolStatuses] = useState([])
  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [poolStatusesData, endpointsData] = await Promise.all([
        poolsApi.getAllPoolStatuses(),
        endpointsApi.getEndpoints()
      ])
      
      setPoolStatuses(poolStatusesData)
      setEndpoints(endpointsData)
    } catch (err) {
      setError('Failed to load dashboard data')
      console.error('Dashboard load error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-danger-500" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading dashboard</h3>
        <p className="mt-1 text-sm text-gray-500">{error}</p>
        <button 
          onClick={loadDashboardData}
          className="mt-4 btn-primary"
        >
          Retry
        </button>
      </div>
    )
  }

  const totalEndpoints = endpoints.length
  const unassignedEndpoints = endpoints.filter(e => !e.pool_id).length
  const totalPools = poolStatuses.length
  const healthyPools = poolStatuses.filter(p => p.overall_status === 'healthy').length

  return (
    <div className="px-4 sm:px-0">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of your package synchronization system
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatusCard
          title="Total Pools"
          value={totalPools}
          icon={CircleStackIcon}
          color="primary"
          subtitle={`${healthyPools} healthy`}
        />
        <StatusCard
          title="Total Endpoints"
          value={totalEndpoints}
          icon={ComputerDesktopIcon}
          color="success"
          subtitle={`${unassignedEndpoints} unassigned`}
        />
        <StatusCard
          title="Sync Rate"
          value={totalPools > 0 ? `${Math.round(poolStatuses.reduce((acc, p) => acc + p.sync_percentage, 0) / totalPools)}%` : '0%'}
          icon={ChartBarIcon}
          color="warning"
          subtitle="Average across pools"
        />
        <StatusCard
          title="Issues"
          value={poolStatuses.filter(p => p.overall_status !== 'healthy').length}
          icon={ExclamationTriangleIcon}
          color="danger"
          subtitle="Pools needing attention"
        />
      </div>

      {/* Pool Status Cards */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Pool Status</h2>
          <Link to="/pools" className="btn-primary">
            Manage Pools
          </Link>
        </div>
        
        {poolStatuses.length === 0 ? (
          <div className="card p-8 text-center">
            <CircleStackIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No pools configured</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating your first package pool
            </p>
            <Link to="/pools" className="mt-4 btn-primary">
              Create Pool
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {poolStatuses.map((pool) => (
              <PoolStatusCard key={pool.pool_id} pool={pool} />
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div className="card p-6">
          <p className="text-gray-500 text-center py-8">
            Activity tracking will be implemented in a future version
          </p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard