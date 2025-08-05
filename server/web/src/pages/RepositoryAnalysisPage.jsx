import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  ArrowLeftIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
  ChartBarIcon,
  TableCellsIcon,
  ExclamationCircleIcon,
  CogIcon,
  EyeSlashIcon,
  EyeIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ServerIcon,
  ClockIcon,
  AdjustmentsHorizontalIcon,
  PlusIcon,
  MinusIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline'
import { repositoriesApi, poolsApi } from '../services/api'

function RepositoryAnalysisPage() {
  const { poolId } = useParams()
  const [pool, setPool] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [packageMatrix, setPackageMatrix] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  
  // Package exclusion management state
  const [excludedPackages, setExcludedPackages] = useState([])
  const [showExclusionModal, setShowExclusionModal] = useState(false)
  const [newExclusionPackage, setNewExclusionPackage] = useState('')
  const [newExclusionReason, setNewExclusionReason] = useState('')
  
  // Conflict resolution state
  const [resolvingConflicts, setResolvingConflicts] = useState({})
  const [conflictResolutions, setConflictResolutions] = useState({})
  
  // Repository information state
  const [repositoryDetails, setRepositoryDetails] = useState([])

  useEffect(() => {
    loadData()
  }, [poolId])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [poolData, analysisData, matrixData, excludedData, repoDetails] = await Promise.all([
        poolsApi.getPool(poolId),
        repositoriesApi.getPoolCompatibilityAnalysis(poolId),
        repositoriesApi.getPackageAvailabilityMatrix(poolId),
        repositoriesApi.getExcludedPackages(poolId).catch(() => []),
        loadRepositoryDetails(poolId).catch(() => [])
      ])
      
      setPool(poolData)
      setAnalysis(analysisData)
      setPackageMatrix(matrixData)
      setExcludedPackages(excludedData)
      setRepositoryDetails(repoDetails)
    } catch (err) {
      setError('Failed to load repository analysis data')
      console.error('Repository analysis load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadRepositoryDetails = async (poolId) => {
    try {
      const pool = await poolsApi.getPool(poolId)
      const endpoints = await Promise.all(
        pool.endpoints.map(async (endpointId) => {
          const repoInfo = await repositoriesApi.getEndpointRepositoryInfo(endpointId)
          return { endpointId, ...repoInfo }
        })
      )
      return endpoints
    } catch (err) {
      console.error('Failed to load repository details:', err)
      return []
    }
  }

  const handleRefreshAnalysis = async () => {
    try {
      setRefreshing(true)
      await repositoriesApi.refreshPoolCompatibilityAnalysis(poolId)
      await loadData()
    } catch (err) {
      console.error('Refresh analysis error:', err)
    } finally {
      setRefreshing(false)
    }
  }

  const formatLastAnalyzed = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'in_sync':
        return <CheckCircleIcon className="h-4 w-4 text-success-500" />
      case 'behind':
        return <ExclamationTriangleIcon className="h-4 w-4 text-danger-500" />
      case 'ahead':
        return <ExclamationCircleIcon className="h-4 w-4 text-warning-500" />
      case 'offline':
        return <XCircleIcon className="h-4 w-4 text-gray-500" />
      default:
        return <InformationCircleIcon className="h-4 w-4 text-gray-500" />
    }
  }

  // Package exclusion management functions
  const handleAddExclusion = async () => {
    if (!newExclusionPackage.trim()) return
    
    try {
      // This would call an API to add package exclusion
      // await repositoriesApi.addPackageExclusion(poolId, {
      //   package_name: newExclusionPackage,
      //   reason: newExclusionReason || 'Manual exclusion'
      // })
      
      // For now, update local state
      const newExclusion = {
        name: newExclusionPackage,
        reason: newExclusionReason || 'Manual exclusion',
        excluded_by: 'user',
        excluded_at: new Date().toISOString()
      }
      
      setExcludedPackages([...excludedPackages, newExclusion])
      setNewExclusionPackage('')
      setNewExclusionReason('')
      setShowExclusionModal(false)
    } catch (err) {
      console.error('Failed to add package exclusion:', err)
    }
  }

  const handleRemoveExclusion = async (packageName) => {
    try {
      // This would call an API to remove package exclusion
      // await repositoriesApi.removePackageExclusion(poolId, packageName)
      
      // For now, update local state
      setExcludedPackages(excludedPackages.filter(pkg => pkg.name !== packageName))
    } catch (err) {
      console.error('Failed to remove package exclusion:', err)
    }
  }

  // Conflict resolution functions
  const handleResolveConflict = async (conflictIndex, resolution) => {
    const conflict = analysis.conflicts[conflictIndex]
    
    try {
      setResolvingConflicts({ ...resolvingConflicts, [conflictIndex]: true })
      
      // This would call an API to resolve the conflict
      // await repositoriesApi.resolvePackageConflict(poolId, {
      //   package_name: conflict.package_name,
      //   resolution_type: resolution.type,
      //   target_version: resolution.version,
      //   target_endpoint: resolution.endpoint
      // })
      
      // For now, update local state
      setConflictResolutions({
        ...conflictResolutions,
        [conflictIndex]: resolution
      })
      
      // Refresh analysis after resolution
      await handleRefreshAnalysis()
    } catch (err) {
      console.error('Failed to resolve conflict:', err)
    } finally {
      setResolvingConflicts({ ...resolvingConflicts, [conflictIndex]: false })
    }
  }

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-success-50 text-success-600 rounded-lg">
              <CheckCircleIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Common Packages</p>
              <p className="text-2xl font-bold text-gray-900">
                {analysis?.common_packages?.length || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-warning-50 text-warning-600 rounded-lg">
              <XCircleIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Excluded Packages</p>
              <p className="text-2xl font-bold text-gray-900">
                {analysis?.excluded_packages?.length || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-danger-50 text-danger-600 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Version Conflicts</p>
              <p className="text-2xl font-bold text-gray-900">
                {analysis?.conflicts?.length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Conflicts Section with Resolution UI */}
      {analysis?.conflicts && analysis.conflicts.length > 0 && (
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-danger-500 mr-2" />
              Version Conflicts ({analysis.conflicts.length})
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-6">
              {analysis.conflicts.map((conflict, index) => {
                const isResolved = conflictResolutions[index]
                const isResolving = resolvingConflicts[index]
                
                return (
                  <div key={index} className={`border rounded-lg p-4 ${
                    isResolved ? 'border-success-200 bg-success-50' : 'border-danger-200 bg-danger-50'
                  }`}>
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h4 className="font-medium text-gray-900 flex items-center">
                          {conflict.package_name}
                          {isResolved && (
                            <CheckCircleIcon className="h-4 w-4 text-success-500 ml-2" />
                          )}
                        </h4>
                        <p className="text-sm text-gray-600 mt-1">
                          {isResolved ? 'Conflict resolved' : conflict.suggested_resolution}
                        </p>
                      </div>
                    </div>
                    
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-700 mb-2">Version by endpoint:</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {Object.entries(conflict.endpoint_versions).map(([endpointId, version]) => {
                          const endpoint = packageMatrix?.endpoints?.find(e => e.id === endpointId)
                          const isTargetVersion = isResolved && conflictResolutions[index]?.endpoint === endpointId
                          
                          return (
                            <div key={endpointId} className={`flex items-center justify-between text-sm p-2 rounded ${
                              isTargetVersion ? 'bg-success-100 border border-success-300' : 'bg-white border border-gray-200'
                            }`}>
                              <span className="text-gray-600">
                                {endpoint?.name || endpointId}
                              </span>
                              <span className="font-mono text-gray-900">{version}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {!isResolved && (
                      <div className="border-t border-gray-200 pt-4">
                        <p className="text-sm font-medium text-gray-700 mb-3">Resolution Options:</p>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(conflict.endpoint_versions).map(([endpointId, version]) => {
                            const endpoint = packageMatrix?.endpoints?.find(e => e.id === endpointId)
                            return (
                              <button
                                key={endpointId}
                                onClick={() => handleResolveConflict(index, {
                                  type: 'use_version',
                                  version,
                                  endpoint: endpointId
                                })}
                                disabled={isResolving}
                                className="btn-secondary text-xs flex items-center"
                              >
                                <CheckCircleIcon className="h-3 w-3 mr-1" />
                                Use {endpoint?.name || endpointId} ({version})
                              </button>
                            )
                          })}
                          <button
                            onClick={() => handleResolveConflict(index, {
                              type: 'exclude_package',
                              package_name: conflict.package_name
                            })}
                            disabled={isResolving}
                            className="btn-danger text-xs flex items-center"
                          >
                            <XCircleIcon className="h-3 w-3 mr-1" />
                            Exclude Package
                          </button>
                        </div>
                      </div>
                    )}

                    {isResolving && (
                      <div className="border-t border-gray-200 pt-4">
                        <div className="flex items-center text-sm text-gray-600">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 mr-2"></div>
                          Resolving conflict...
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Excluded Packages */}
      {analysis?.excluded_packages && analysis.excluded_packages.length > 0 && (
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <XCircleIcon className="h-5 w-5 text-warning-500 mr-2" />
              Excluded Packages ({analysis.excluded_packages.length})
            </h3>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Package
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Version
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Repository
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reason
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {analysis.excluded_packages.slice(0, 50).map((pkg, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {pkg.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                        {pkg.version}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {pkg.repository}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {pkg.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {analysis.excluded_packages.length > 50 && (
                <div className="px-6 py-3 text-sm text-gray-500 text-center border-t">
                  Showing first 50 of {analysis.excluded_packages.length} excluded packages
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderMatrixTab = () => {
    if (!packageMatrix || !packageMatrix.packages) {
      return (
        <div className="text-center py-12">
          <TableCellsIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No package matrix data</h3>
          <p className="mt-1 text-sm text-gray-500">Package availability matrix is not available</p>
        </div>
      )
    }

    const packages = Object.keys(packageMatrix.packages).slice(0, 100) // Limit for performance
    const endpoints = packageMatrix.endpoints || []

    return (
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <TableCellsIcon className="h-5 w-5 text-primary-500 mr-2" />
            Package Availability Matrix
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Showing first 100 packages across {endpoints.length} endpoints
          </p>
        </div>
        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50">
                    Package
                  </th>
                  {endpoints.map((endpoint) => (
                    <th key={endpoint.id} className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider min-w-24">
                      <div className="flex flex-col items-center">
                        {getStatusIcon(endpoint.sync_status)}
                        <span className="mt-1">{endpoint.name}</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {packages.map((packageName) => (
                  <tr key={packageName}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white">
                      {packageName}
                    </td>
                    {endpoints.map((endpoint) => {
                      const version = packageMatrix.packages[packageName][endpoint.id]
                      return (
                        <td key={endpoint.id} className="px-3 py-3 whitespace-nowrap text-center text-xs">
                          {version ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-success-100 text-success-800 font-mono">
                              {version}
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-gray-500">
                              N/A
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  const renderExclusionsTab = () => (
    <div className="space-y-6">
      {/* Add Exclusion Section */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <PlusIcon className="h-5 w-5 text-primary-500 mr-2" />
            Add Package Exclusion
          </h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="form-label">Package Name</label>
              <input
                type="text"
                value={newExclusionPackage}
                onChange={(e) => setNewExclusionPackage(e.target.value)}
                placeholder="e.g., firefox, chromium"
                className="form-input"
              />
            </div>
            <div>
              <label className="form-label">Reason (Optional)</label>
              <input
                type="text"
                value={newExclusionReason}
                onChange={(e) => setNewExclusionReason(e.target.value)}
                placeholder="e.g., Incompatible with system"
                className="form-input"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleAddExclusion}
                disabled={!newExclusionPackage.trim()}
                className="btn-primary w-full"
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Exclusion
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Current Exclusions */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <EyeSlashIcon className="h-5 w-5 text-warning-500 mr-2" />
            Excluded Packages ({excludedPackages.length})
          </h3>
        </div>
        <div className="p-6">
          {excludedPackages.length === 0 ? (
            <div className="text-center py-8">
              <EyeSlashIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No excluded packages</h3>
              <p className="mt-1 text-sm text-gray-500">Add packages to exclude them from synchronization</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Package Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reason
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Excluded By
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {excludedPackages.map((pkg, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {pkg.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {pkg.reason || 'No reason provided'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`status-badge ${
                          pkg.excluded_by === 'system' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {pkg.excluded_by === 'system' ? 'System' : 'Manual'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(pkg.excluded_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {pkg.excluded_by !== 'system' && (
                          <button
                            onClick={() => handleRemoveExclusion(pkg.name)}
                            className="text-danger-600 hover:text-danger-900"
                          >
                            <MinusIcon className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Automatic Exclusions from Analysis */}
      {analysis?.excluded_packages && analysis.excluded_packages.length > 0 && (
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <CogIcon className="h-5 w-5 text-blue-500 mr-2" />
              Automatically Excluded Packages ({analysis.excluded_packages.length})
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              These packages are automatically excluded due to compatibility issues
            </p>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Package
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Version
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Repository
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reason
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {analysis.excluded_packages.slice(0, 50).map((pkg, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {pkg.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                        {pkg.version}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {pkg.repository}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {pkg.description}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            // Add to manual exclusions to override automatic exclusion
                            const newExclusion = {
                              name: pkg.name,
                              reason: 'Override automatic exclusion',
                              excluded_by: 'user',
                              excluded_at: new Date().toISOString()
                            }
                            setExcludedPackages([...excludedPackages, newExclusion])
                          }}
                          className="text-primary-600 hover:text-primary-900 text-xs"
                        >
                          Override
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {analysis.excluded_packages.length > 50 && (
                <div className="px-6 py-3 text-sm text-gray-500 text-center border-t">
                  Showing first 50 of {analysis.excluded_packages.length} automatically excluded packages
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderRepositoriesTab = () => (
    <div className="space-y-6">
      {/* Repository Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-primary-50 text-primary-600 rounded-lg">
              <ServerIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Endpoints</p>
              <p className="text-2xl font-bold text-gray-900">
                {repositoryDetails.length}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-success-50 text-success-600 rounded-lg">
              <DocumentTextIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Repositories</p>
              <p className="text-2xl font-bold text-gray-900">
                {repositoryDetails.reduce((total, endpoint) => 
                  total + (endpoint.repositories?.length || 0), 0
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-3 bg-warning-50 text-warning-600 rounded-lg">
              <ClockIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Last Updated</p>
              <p className="text-sm font-bold text-gray-900">
                {repositoryDetails.length > 0 ? 
                  new Date(Math.max(...repositoryDetails.map(r => 
                    new Date(r.last_updated || 0).getTime()
                  ))).toLocaleDateString() : 'N/A'
                }
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Repository Details by Endpoint */}
      {repositoryDetails.map((endpoint, index) => (
        <div key={index} className="card">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 flex items-center">
                <ComputerDesktopIcon className="h-5 w-5 text-primary-500 mr-2" />
                {endpoint.name || `Endpoint ${endpoint.endpointId}`}
              </h3>
              <div className="flex items-center space-x-2">
                {getStatusIcon(endpoint.sync_status)}
                <span className="text-sm text-gray-500">
                  {endpoint.repositories?.length || 0} repositories
                </span>
              </div>
            </div>
          </div>
          <div className="p-6">
            {!endpoint.repositories || endpoint.repositories.length === 0 ? (
              <div className="text-center py-8">
                <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No repository data</h3>
                <p className="mt-1 text-sm text-gray-500">Repository information not available for this endpoint</p>
              </div>
            ) : (
              <div className="space-y-4">
                {endpoint.repositories.map((repo, repoIndex) => (
                  <div key={repoIndex} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium text-gray-900">{repo.name}</h4>
                        <p className="text-sm text-gray-500 mt-1">{repo.url}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">
                          {repo.package_count || 0} packages
                        </p>
                        <p className="text-xs text-gray-500">
                          {repo.architecture || 'x86_64'}
                        </p>
                      </div>
                    </div>
                    
                    {repo.last_sync && (
                      <div className="flex items-center text-xs text-gray-500">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Last synced: {new Date(repo.last_sync).toLocaleString()}
                      </div>
                    )}
                    
                    {repo.status && (
                      <div className="mt-2">
                        <span className={`status-badge ${
                          repo.status === 'active' ? 'status-in-sync' :
                          repo.status === 'error' ? 'status-behind' :
                          'status-offline'
                        }`}>
                          {repo.status}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {repositoryDetails.length === 0 && (
        <div className="text-center py-12">
          <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No repository details</h3>
          <p className="mt-1 text-sm text-gray-500">Repository information will appear here once endpoints are connected</p>
        </div>
      )}
    </div>
  )

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
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading analysis</h3>
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
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Link
              to={`/pools/${poolId}`}
              className="mr-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md"
            >
              <ArrowLeftIcon className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Repository Analysis</h1>
              <p className="mt-1 text-gray-600">Pool: {pool.name}</p>
            </div>
          </div>
          
          <button
            onClick={handleRefreshAnalysis}
            disabled={refreshing}
            className="btn-primary flex items-center"
          >
            <ArrowPathIcon className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Analysis'}
          </button>
        </div>

        {/* Analysis Info */}
        {analysis && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center">
              <InformationCircleIcon className="h-5 w-5 text-blue-500 mr-2" />
              <span className="text-sm text-blue-700">
                Last analyzed: {formatLastAnalyzed(analysis.last_analyzed)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <ChartBarIcon className="h-4 w-4 inline mr-2" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('matrix')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'matrix'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <TableCellsIcon className="h-4 w-4 inline mr-2" />
            Package Matrix
          </button>
          <button
            onClick={() => setActiveTab('exclusions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'exclusions'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <AdjustmentsHorizontalIcon className="h-4 w-4 inline mr-2" />
            Exclusion Management
          </button>
          <button
            onClick={() => setActiveTab('repositories')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'repositories'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <ServerIcon className="h-4 w-4 inline mr-2" />
            Repository Details
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && renderOverviewTab()}
      {activeTab === 'matrix' && renderMatrixTab()}
      {activeTab === 'exclusions' && renderExclusionsTab()}
      {activeTab === 'repositories' && renderRepositoriesTab()}
    </div>
  )
}

export default RepositoryAnalysisPage