import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Pool API functions
export const poolsApi = {
  // Get all pools
  async getPools() {
    const response = await api.get('/pools')
    return response.data
  },

  // Get pool by ID
  async getPool(poolId) {
    const response = await api.get(`/pools/${poolId}`)
    return response.data
  },

  // Create new pool
  async createPool(poolData) {
    const response = await api.post('/pools', poolData)
    return response.data
  },

  // Update pool
  async updatePool(poolId, poolData) {
    const response = await api.put(`/pools/${poolId}`, poolData)
    return response.data
  },

  // Delete pool
  async deletePool(poolId) {
    await api.delete(`/pools/${poolId}`)
  },

  // Get pool status
  async getPoolStatus(poolId) {
    const response = await api.get(`/pools/${poolId}/status`)
    return response.data
  },

  // Get all pool statuses
  async getAllPoolStatuses() {
    const response = await api.get('/dashboard/pool-statuses')
    return response.data
  },

  // Assign endpoint to pool
  async assignEndpoint(poolId, endpointId) {
    await api.post(`/pools/${poolId}/endpoints`, { endpoint_id: endpointId })
  },

  // Remove endpoint from pool
  async removeEndpoint(poolId, endpointId) {
    await api.delete(`/pools/${poolId}/endpoints/${endpointId}`)
  },

  // Move endpoint between pools
  async moveEndpoint(sourcePoolId, endpointId, targetPoolId) {
    await api.put(`/pools/${sourcePoolId}/endpoints/${endpointId}/move/${targetPoolId}`)
  }
}

// Endpoints API functions
export const endpointsApi = {
  // Get all endpoints
  async getEndpoints(poolId = null) {
    const params = poolId ? { pool_id: poolId } : {}
    const response = await api.get('/endpoints', { params })
    return response.data
  },

  // Get endpoint by ID
  async getEndpoint(endpointId) {
    const response = await api.get(`/endpoints/${endpointId}`)
    return response.data
  },

  // Update endpoint status
  async updateEndpointStatus(endpointId, status) {
    await api.put(`/endpoints/${endpointId}/status`, { status })
  },

  // Remove endpoint
  async removeEndpoint(endpointId) {
    await api.delete(`/endpoints/${endpointId}`)
  },

  // Get repository info for endpoint
  async getRepositoryInfo(endpointId) {
    const response = await api.get(`/endpoints/${endpointId}/repositories`)
    return response.data
  },

  // Assign endpoint to pool
  async assignToPool(endpointId, poolId) {
    await api.put(`/endpoints/${endpointId}/pool`, null, { params: { pool_id: poolId } })
  },

  // Remove endpoint from pool
  async removeFromPool(endpointId) {
    await api.delete(`/endpoints/${endpointId}/pool`)
  }
}

// Sync API functions
export const syncApi = {
  // Trigger sync operation
  async triggerSync(endpointId) {
    const response = await api.post(`/sync/${endpointId}/sync`)
    return response.data
  },

  // Set as latest
  async setAsLatest(endpointId) {
    const response = await api.post(`/sync/${endpointId}/set-latest`)
    return response.data
  },

  // Revert to previous
  async revertToPrevious(endpointId) {
    const response = await api.post(`/sync/${endpointId}/revert`)
    return response.data
  },

  // Get sync status
  async getSyncStatus(endpointId) {
    const response = await api.get(`/sync/${endpointId}/status`)
    return response.data
  }
}

// Repository Analysis API functions
export const repositoriesApi = {
  // Get compatibility analysis for a pool
  async getPoolCompatibilityAnalysis(poolId) {
    const response = await api.get(`/repositories/analysis/${poolId}`)
    return response.data
  },

  // Refresh compatibility analysis for a pool
  async refreshPoolCompatibilityAnalysis(poolId) {
    const response = await api.post(`/repositories/analysis/${poolId}/refresh`)
    return response.data
  },

  // Get package availability matrix for a pool
  async getPackageAvailabilityMatrix(poolId) {
    const response = await api.get(`/repositories/matrix/${poolId}`)
    return response.data
  },

  // Get excluded packages for a pool
  async getExcludedPackages(poolId) {
    const response = await api.get(`/repositories/excluded/${poolId}`)
    return response.data
  },

  // Get repository info for an endpoint
  async getEndpointRepositoryInfo(endpointId) {
    const response = await api.get(`/repositories/endpoint/${endpointId}`)
    return response.data
  },

  // Get package conflicts for a pool
  async getPackageConflicts(poolId) {
    const response = await api.get(`/repositories/conflicts/${poolId}`)
    return response.data
  }
}

// Dashboard API functions
export const dashboardApi = {
  // Get dashboard metrics
  async getMetrics() {
    const response = await api.get('/dashboard/metrics')
    return response.data
  },

  // Get pool statuses
  async getPoolStatuses() {
    const response = await api.get('/dashboard/pool-statuses')
    return response.data
  },

  // Get system statistics
  async getSystemStats() {
    const response = await api.get('/dashboard/system-stats')
    return response.data
  },

  // Health check
  async healthCheck() {
    const response = await api.get('/dashboard/health')
    return response.data
  }
}

export default api