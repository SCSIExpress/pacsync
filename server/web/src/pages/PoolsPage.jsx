import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  PlusIcon, 
  PencilIcon, 
  TrashIcon,
  CircleStackIcon,
  ComputerDesktopIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { poolsApi } from '../services/api'
import CreatePoolModal from '../components/CreatePoolModal'
import EditPoolModal from '../components/EditPoolModal'
import DeleteConfirmModal from '../components/DeleteConfirmModal'

function PoolCard({ pool, onEdit, onDelete }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success'
      case 'warning': return 'warning'
      case 'critical': return 'danger'
      default: return 'primary'
    }
  }

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center">
            <CircleStackIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">{pool.name}</h3>
          </div>
          {pool.description && (
            <p className="mt-1 text-sm text-gray-500">{pool.description}</p>
          )}
          
          <div className="mt-4 flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-500">
              <ComputerDesktopIcon className="h-4 w-4 mr-1" />
              {pool.endpoints.length} endpoints
            </div>
            <div className="flex items-center text-sm text-gray-500">
              <span className={`inline-block w-2 h-2 rounded-full mr-1 ${
                pool.sync_policy?.auto_sync ? 'bg-success-500' : 'bg-gray-400'
              }`} />
              {pool.sync_policy?.auto_sync ? 'Auto-sync enabled' : 'Manual sync'}
            </div>
          </div>
          
          {pool.sync_policy?.exclude_packages?.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">
                Excludes: {pool.sync_policy.exclude_packages.slice(0, 3).join(', ')}
                {pool.sync_policy.exclude_packages.length > 3 && ` +${pool.sync_policy.exclude_packages.length - 3} more`}
              </span>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2 ml-4">
          <button
            onClick={() => onEdit(pool)}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md"
            title="Edit pool"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(pool)}
            className="p-2 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded-md"
            title="Delete pool"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <Link
          to={`/pools/${pool.id}`}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          View details →
        </Link>
      </div>
    </div>
  )
}

function PoolsPage() {
  const [pools, setPools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingPool, setEditingPool] = useState(null)
  const [deletingPool, setDeletingPool] = useState(null)

  useEffect(() => {
    loadPools()
  }, [])

  const loadPools = async () => {
    try {
      setLoading(true)
      const poolsData = await poolsApi.getPools()
      setPools(poolsData)
    } catch (err) {
      setError('Failed to load pools')
      console.error('Pools load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePool = async (poolData) => {
    try {
      await poolsApi.createPool(poolData)
      setShowCreateModal(false)
      await loadPools()
    } catch (err) {
      console.error('Create pool error:', err)
      throw err
    }
  }

  const handleEditPool = async (poolData) => {
    try {
      await poolsApi.updatePool(editingPool.id, poolData)
      setEditingPool(null)
      await loadPools()
    } catch (err) {
      console.error('Edit pool error:', err)
      throw err
    }
  }

  const handleDeletePool = async () => {
    try {
      await poolsApi.deletePool(deletingPool.id)
      setDeletingPool(null)
      await loadPools()
    } catch (err) {
      console.error('Delete pool error:', err)
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

  if (error) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-danger-500" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading pools</h3>
        <p className="mt-1 text-sm text-gray-500">{error}</p>
        <button 
          onClick={loadPools}
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Package Pools</h1>
          <p className="mt-2 text-gray-600">
            Manage package synchronization pools and their configurations
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Create Pool
        </button>
      </div>

      {/* Pools Grid */}
      {pools.length === 0 ? (
        <div className="card p-12 text-center">
          <CircleStackIcon className="mx-auto h-16 w-16 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No pools configured</h3>
          <p className="mt-2 text-gray-500 max-w-sm mx-auto">
            Create your first package pool to start synchronizing packages across your endpoints
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-6 btn-primary"
          >
            Create Your First Pool
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {pools.map((pool) => (
            <PoolCard
              key={pool.id}
              pool={pool}
              onEdit={setEditingPool}
              onDelete={setDeletingPool}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {showCreateModal && (
        <CreatePoolModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreatePool}
        />
      )}

      {editingPool && (
        <EditPoolModal
          pool={editingPool}
          onClose={() => setEditingPool(null)}
          onSubmit={handleEditPool}
        />
      )}

      {deletingPool && (
        <DeleteConfirmModal
          title="Delete Pool"
          message={`Are you sure you want to delete the pool "${deletingPool.name}"? This action cannot be undone and will remove all endpoint assignments.`}
          onClose={() => setDeletingPool(null)}
          onConfirm={handleDeletePool}
        />
      )}
    </div>
  )
}

export default PoolsPage