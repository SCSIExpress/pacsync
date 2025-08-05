import React from 'react'
import { useDrag } from 'react-dnd'
import { formatDistanceToNow } from 'date-fns'
import { 
  ComputerDesktopIcon,
  TrashIcon,
  GlobeAltIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

function EndpointCard({ endpoint, onRemove, showRemove = false, draggable = false, showPool = false }) {
  const [{ isDragging }, drag] = useDrag({
    type: 'endpoint',
    item: { id: endpoint.id, poolId: endpoint.pool_id },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }, [endpoint.id, endpoint.pool_id])

  const getStatusColor = (status) => {
    switch (status) {
      case 'in_sync': return 'success'
      case 'ahead': return 'warning'
      case 'behind': return 'danger'
      case 'offline': return 'gray'
      default: return 'gray'
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'in_sync': return 'In Sync'
      case 'ahead': return 'Ahead'
      case 'behind': return 'Behind'
      case 'offline': return 'Offline'
      default: return 'Unknown'
    }
  }

  const formatLastSeen = (lastSeen) => {
    if (!lastSeen) return 'Never'
    try {
      return formatDistanceToNow(new Date(lastSeen), { addSuffix: true })
    } catch {
      return 'Unknown'
    }
  }

  const cardRef = draggable ? drag : null

  return (
    <div
      ref={cardRef}
      className={`card p-4 transition-all ${
        isDragging ? 'opacity-50 transform rotate-2' : ''
      } ${draggable ? 'cursor-move hover:shadow-md' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="flex-shrink-0">
            <ComputerDesktopIcon className="h-5 w-5 text-gray-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {endpoint.name}
            </h3>
            <div className="flex items-center mt-1 text-xs text-gray-500">
              <GlobeAltIcon className="h-3 w-3 mr-1" />
              <span className="truncate">{endpoint.hostname}</span>
            </div>
            {endpoint.last_seen && (
              <div className="flex items-center mt-1 text-xs text-gray-500">
                <ClockIcon className="h-3 w-3 mr-1" />
                <span>Last seen {formatLastSeen(endpoint.last_seen)}</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-2 ml-2">
          <span className={`status-${getStatusColor(endpoint.sync_status)}`}>
            {getStatusText(endpoint.sync_status)}
          </span>
          {showRemove && onRemove && (
            <button
              onClick={() => onRemove(endpoint.id)}
              className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded"
              title="Remove endpoint"
            >
              <TrashIcon className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
      
      {showPool && endpoint.pool_id && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <span className="text-xs text-gray-500">
            Assigned to pool
          </span>
        </div>
      )}
    </div>
  )
}

export default EndpointCard