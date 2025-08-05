import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useDrop } from 'react-dnd'
import { 
  ArrowLeftIcon,
  ComputerDesktopIcon,
  PencilIcon,
  ChartBarIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { poolsApi, endpointsApi } from '../services/api'
import EndpointCard from '../components/EndpointCard'
import EditPoolModal from '../components/EditPoolModal'

function PoolDetailPage() {
  const { poolId } = useParams()
  const [pool, setPool] = useState(null)
  const [poolStatus, setPoolStatus] = useState(null)
  const [assignedEndpoints, setAssignedEndpoints] = useState([])
  const [unassignedEndpoints, setUnassignedEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingPool, setEditingPool] = useState(null)

  const [{ isOver }, drop] = useDrop({
    accept: 'endpoint',
    drop: (item) => {
      if (item.poolId !== poolId) {
        handleAssignEndpoint(item.id)
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  })

  useEffect(() => {
    loadPoolData()
  }, [poolId])

  const loadPoolData = async () => {
    try {
      setLoading(true)
      const [poolData, poolStatusData, allEndpoints] = await Promise.all([
        poolsApi.getPool(poolId),
        poolsApi.getPoolStatus(poolId),
        endpointsApi.getEndpoints()
      ])
      
      setPool(poolData)
      setPoolStatus(poolStatusData)
      
      const assigned = allEndpoints.filter(e => e.pool_id === poolId)
      const unassigned = allEndpoints.filter(e => !e.pool_id)
      
      setAssignedEndpoints(assigned)
      setUnassignedEndpoints(unassigned)
    } catch (err) {
      setError('Failed to load pool data')
      console.error('Pool detail load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAssignEndpoint = async (endpointId) => {
    try {
      await poolsApi.assignEndpoint(poolId, endpointId)
      await loadPoolData()
    } catch (err) {
      console.error('Assign endpoint error:', err)
    }
  }

  const handleRemoveEndpoint = async (endpointId) => {
    try {
      await poolsApi.removeEndpoint(poolId, endpointId)
      await loadPoolData()
    } catch (err) {
      console.error('Remove endpoint error:', err)
    }
  }

  const handleEditPool = async (poolData) => {
    try {
      await poolsApi.updatePool(poolId, poolData)
      setEditingPool(null)
      await loadPoolData()
    } catch (err) {
      console.error('Edit pool error:', err)
      throw err
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !pool) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-danger-500" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading pool</h3>
        <p className="mt-1 text-sm text-gray-500">{error || 'Pool not found'}</p>
        <Link to="/pools" className="mt-4 btn-primary">
          Back to Pools
        </Link>
      </div>
    )
  }

  return (
    <div className="px-4 sm:px-0">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Link
            to="/pools"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{pool.name}</h1>
            {pool.description && (
              <p className="mt-2 text-gray-600">{pool.description}</p>
            )}
          </div>
          <div className="flex space-x-3">
            <Link
              to={`/pools/${poolId}/analysis`}
              className="btn-secondary flex items-center"
            >
              <ChartBarIcon className="h-4 w-4 mr-2" />
              Repository Analysis
            </Link>
            <button
              onClick={() => setEditingPool(pool)}
              className="btn-secondary flex items-center"
            >
              <PencilIcon className="h-4 w-4 mr-2" />
              Edit Pool
            </button>
          </div>
        </div>

        {/* Pool Status */}
        {poolStatus && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="card p-4">
              <div className="flex items-center">
                <div className="p-2 bg-primary-50 text-primary-600 rounded-lg">
                  <ComputerDesktopIcon className="h-5 w-5" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Total Endpoints</p>
                  <p className="text-lg font-semibold text-gray-900">{poolStatus.total_endpoints}</p>
                </div>
              </div>
            </div>
            
            <div className="card p-4">
              <div className="flex items-center">
                <div className="p-2 bg-success-50 text-success-600 rounded-lg">
                  <ChartBarIcon className="h-5 w-5" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-600">Sync Rate</p>
                  <p className="text-lg font-semibold text-gray-900">{poolStatus.sync_percentage}%</p>
                </div>
              </div>
            </div>
            
            <div className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">In Sync</p>
                  <p className="text-lg font-semibold text-success-600">{poolStatus.in_sync_count}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Behind</p>
                  <p className="text-lg font-semibold text-danger-600">{poolStatus.behind_count}</p>
                </div>
              </div>
            </div>
            
            <div className="card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Ahead</p>
                  <p className="text-lg font-semibold text-warning-600">{poolStatus.ahead_count}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Offline</p>
                  <p className="text-lg font-semibold text-gray-600">{poolStatus.offline_count}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Assigned Endpoints */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Pool Endpoints ({assignedEndpoints.length})
          </h2>
          
          <div
            ref={drop}
            className={`min-h-64 p-4 border-2 border-dashed rounded-lg transition-colors ${
              isOver 
                ? 'border-primary-400 bg-primary-50' 
                : 'border-gray-300 bg-gray-50'
            }`}
          >
            {assignedEndpoints.length === 0 ? (
              <div className="text-center py-12">
                <ComputerDesktopIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No endpoints assigned</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Drag endpoints from the right panel to assign them to this pool
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {assignedEndpoints.map((endpoint) => (
                  <EndpointCard
                    key={endpoint.id}
                    endpoint={endpoint}
                    onRemove={() => handleRemoveEndpoint(endpoint.id)}
                    showRemove
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Unassigned Endpoints */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Available Endpoints ({unassignedEndpoints.length})
          </h2>
          
          <div className="min-h-64 p-4 bg-white border border-gray-200 rounded-lg">
            {unassignedEndpoints.length === 0 ? (
              <div className="text-center py-12">
                <ComputerDesktopIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No available endpoints</h3>
                <p className="mt-1 text-sm text-gray-500">
                  All endpoints are currently assigned to pools
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {unassignedEndpoints.map((endpoint) => (
                  <EndpointCard
                    key={endpoint.id}
                    endpoint={endpoint}
                    draggable
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pool Configuration */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Configuration</h2>
        <div className="card p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Sync Policy</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex items-center">
                  <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                    pool.sync_policy?.auto_sync ? 'bg-success-500' : 'bg-gray-400'
                  }`} />
                  Auto-sync: {pool.sync_policy?.auto_sync ? 'Enabled' : 'Disabled'}
                </div>
                <div className="flex items-center">
                  <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                    pool.sync_policy?.include_aur ? 'bg-success-500' : 'bg-gray-400'
                  }`} />
                  AUR packages: {pool.sync_policy?.include_aur ? 'Included' : 'Excluded'}
                </div>
                <div>
                  Conflict resolution: {pool.sync_policy?.conflict_resolution || 'manual'}
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Excluded Packages</h3>
              {pool.sync_policy?.exclude_packages?.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {pool.sync_policy.exclude_packages.map((pkg, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800"
                    >
                      {pkg}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No packages excluded</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Edit Pool Modal */}
      {editingPool && (
        <EditPoolModal
          pool={editingPool}
          onClose={() => setEditingPool(null)}
          onSubmit={handleEditPool}
        />
      )}
    </div>
  )
}

export default PoolDetailPage