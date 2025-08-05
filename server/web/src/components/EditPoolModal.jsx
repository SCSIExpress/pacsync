import React, { useState, useEffect } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'

function EditPoolModal({ pool, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    sync_policy: {
      auto_sync: false,
      exclude_packages: [],
      include_aur: false,
      conflict_resolution: 'manual'
    }
  })
  const [excludePackageInput, setExcludePackageInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (pool) {
      setFormData({
        name: pool.name || '',
        description: pool.description || '',
        sync_policy: {
          auto_sync: pool.sync_policy?.auto_sync || false,
          exclude_packages: pool.sync_policy?.exclude_packages || [],
          include_aur: pool.sync_policy?.include_aur || false,
          conflict_resolution: pool.sync_policy?.conflict_resolution || 'manual'
        }
      })
    }
  }, [pool])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await onSubmit(formData)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update pool')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSyncPolicyChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      sync_policy: {
        ...prev.sync_policy,
        [field]: value
      }
    }))
  }

  const addExcludePackage = () => {
    if (excludePackageInput.trim()) {
      const packages = excludePackageInput.split(',').map(p => p.trim()).filter(p => p)
      handleSyncPolicyChange('exclude_packages', [
        ...formData.sync_policy.exclude_packages,
        ...packages
      ])
      setExcludePackageInput('')
    }
  }

  const removeExcludePackage = (index) => {
    const newPackages = [...formData.sync_policy.exclude_packages]
    newPackages.splice(index, 1)
    handleSyncPolicyChange('exclude_packages', newPackages)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addExcludePackage()
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Edit Pool</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <div>
              <label className="form-label">Pool Name *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="form-input"
                placeholder="Enter pool name"
              />
            </div>

            <div>
              <label className="form-label">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="form-input"
                rows={3}
                placeholder="Optional description for this pool"
              />
            </div>
          </div>

          {/* Sync Policy */}
          <div className="space-y-4">
            <h4 className="text-md font-medium text-gray-900">Sync Policy</h4>
            
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.sync_policy.auto_sync}
                  onChange={(e) => handleSyncPolicyChange('auto_sync', e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-700">Enable automatic synchronization</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.sync_policy.include_aur}
                  onChange={(e) => handleSyncPolicyChange('include_aur', e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-700">Include AUR packages</span>
              </label>
            </div>

            <div>
              <label className="form-label">Conflict Resolution</label>
              <select
                value={formData.sync_policy.conflict_resolution}
                onChange={(e) => handleSyncPolicyChange('conflict_resolution', e.target.value)}
                className="form-input"
              >
                <option value="manual">Manual resolution</option>
                <option value="newest">Use newest version</option>
                <option value="oldest">Use oldest version</option>
              </select>
            </div>

            <div>
              <label className="form-label">Excluded Packages</label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={excludePackageInput}
                  onChange={(e) => setExcludePackageInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="form-input flex-1"
                  placeholder="Package names (comma-separated)"
                />
                <button
                  type="button"
                  onClick={addExcludePackage}
                  className="btn-secondary"
                >
                  Add
                </button>
              </div>
              
              {formData.sync_policy.exclude_packages.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {formData.sync_policy.exclude_packages.map((pkg, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800"
                    >
                      {pkg}
                      <button
                        type="button"
                        onClick={() => removeExcludePackage(index)}
                        className="ml-1 text-gray-500 hover:text-gray-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-danger-50 border border-danger-200 rounded-md">
              <p className="text-sm text-danger-600">{error}</p>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
            >
              {loading ? 'Updating...' : 'Update Pool'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EditPoolModal