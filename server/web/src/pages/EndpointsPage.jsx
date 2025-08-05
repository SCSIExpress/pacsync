import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  ComputerDesktopIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  FunnelIcon
} from '@heroicons/react/24/outline'
import { endpointsApi, poolsApi } from '../services/api'
import EndpointCard from '../components/EndpointCard'

function EndpointsPage() {
  const [endpoints, setEndpoints] = useState([])
  const [pools, setPools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterPool, setFilterPool] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [endpointsData, poolsData] = await Promise.all([
        endpointsApi.getEndpoints(),
        poolsApi.getPools()
      ])
      
      setEndpoints(endpointsData)
      setPools(poolsData)
    } catch (err) {
      setError('Failed to load endpoints')
      console.error('Endpoints load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveEndpoint = async (endpointId) => {
    try {
      await endpointsApi.removeEndpoint(endpointId)
      await loadData()
    } catch (err) {
      console.error('Remove endpoint error:', err)
    }
  }

  const getPoolName = (poolId) => {
    const pool = pools.find(p => p.id === poolId)
    return pool ? pool.name : 'Unknown Pool'
  }

  // Filter endpoints based on search and filters
  const filteredEndpoints = endpoints.filter(endpoint => {
    const matchesSearch = endpoint.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         endpoint.hostname.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesPool = filterPool === 'all' || 
                       (filterPool === 'unassigned' && !endpoint.pool_id) ||
                       endpoint.pool_id === filterPool
    
    const matchesStatus = filterStatus === 'all' || endpoint.sync_status === filterStatus
    
    return matchesSearch && matchesPool && matchesStatus
  })

  // Group endpoints by pool
  const groupedEndpoints = filteredEndpoints.reduce((groups, endpoint) => {
    const poolId = endpoint.pool_id || 'unassigned'
    if (!groups[poolId]) {
      groups[poolId] = []
    }
    groups[poolId].push(endpoint)
    return groups
  }, {})

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
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading endpoints</h3>
        <p className="mt-1 text-sm text-gray-500">{error}</p>
        <button 
          onClick={loadData}
          className="mt-4 btn-primary"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="px-4 sm:px-0">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Endpoints</h1>
        <p className="mt-2 text-gray-600">
          Manage all registered endpoints and their pool assignments
        </p>
      </div>

      {/* Filters and Search */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search endpoints..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>

        {/* Pool Filter */}
        <div className="relative">
          <select
            value={filterPool}
            onChange={(e) => setFilterPool(e.target.value)}
            className="form-input pr-10 appearance-none"
          >
            <option value="all">All Pools</option>
            <option value="unassigned">Unassigned</option>
            {pools.map(pool => (
              <option key={pool.id} value={pool.id}>{pool.name}</option>
            ))}
          </select>
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
          </div>
        </div>

        {/* Status Filter */}
        <div className="relative">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="form-input pr-10 appearance-none"
          >
            <option value="all">All Status</option>
            <option value="in_sync">In Sync</option>
            <option value="ahead">Ahead</option>
            <option value="behind">Behind</option>
            <option value="offline">Offline</option>
          </select>
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Results Summary */}
      <div className="mb-6 text-sm text-gray-600">
        Showing {filteredEndpoints.length} of {endpoints.length} endpoints
      </div>

      {/* Endpoints */}
      {filteredEndpoints.length === 0 ? (
        <div className="card p-12 text-center">
          <ComputerDesktopIcon className="mx-auto h-16 w-16 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            {searchTerm || filterPool !== 'all' || filterStatus !== 'all' 
              ? 'No endpoints match your filters' 
              : 'No endpoints registered'
            }
          </h3>
          <p className="mt-2 text-gray-500">
            {searchTerm || filterPool !== 'all' || filterStatus !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'Endpoints will appear here once they register with the server'
            }
          </p>
          {(searchTerm || filterPool !== 'all' || filterStatus !== 'all') && (
            <button
              onClick={() => {
                setSearchTerm('')
                setFilterPool('all')
                setFilterStatus('all')
              }}
              className="mt-4 btn-secondary"
            >
              Clear Filters
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(groupedEndpoints).map(([poolId, poolEndpoints]) => (
            <div key={poolId}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium text-gray-900">
                  {poolId === 'unassigned' ? (
                    'Unassigned Endpoints'
                  ) : (
                    <Link 
                      to={`/pools/${poolId}`}
                      className="hover:text-primary-600"
                    >
                      {getPoolName(poolId)} Pool
                    </Link>
                  )}
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    ({poolEndpoints.length})
                  </span>
                </h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {poolEndpoints.map((endpoint) => (
                  <EndpointCard
                    key={endpoint.id}
                    endpoint={endpoint}
                    onRemove={() => handleRemoveEndpoint(endpoint.id)}
                    showRemove
                    showPool={poolId === 'unassigned'}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default EndpointsPage