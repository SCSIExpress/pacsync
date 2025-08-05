# Pacman Sync Utility Web UI

This is the React-based web interface for the Pacman Sync Utility server.

## Features

### Pool Management Interface
- ✅ Create, edit, and delete package pools
- ✅ Configure sync policies (auto-sync, AUR inclusion, conflict resolution)
- ✅ Manage excluded packages
- ✅ Real-time pool status dashboard

### Endpoint Assignment Interface
- ✅ Drag-and-drop endpoint assignment to pools
- ✅ Visual endpoint status indicators (in sync, ahead, behind, offline)
- ✅ Endpoint filtering and search
- ✅ Pool-based endpoint grouping

### Real-time Status Dashboard
- ✅ System overview with key metrics
- ✅ Pool health monitoring
- ✅ Endpoint status tracking
- ✅ Sync percentage indicators

## Development

### Prerequisites
- Node.js 16+ and npm
- Running Pacman Sync Utility server

### Setup
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### API Integration
The web UI communicates with the server via REST API endpoints:
- `/api/pools` - Pool management
- `/api/endpoints` - Endpoint management
- `/api/sync` - Synchronization operations

### Architecture
- **React 18** with functional components and hooks
- **React Router** for client-side routing
- **React DnD** for drag-and-drop functionality
- **Tailwind CSS** for styling
- **Axios** for API communication
- **Heroicons** for icons
- **date-fns** for date formatting

## Production Deployment

The built files are served by the FastAPI server automatically when available in the `dist/` directory. The server handles:
- Static file serving
- SPA routing fallback
- API proxy configuration

## Requirements Fulfilled

This implementation fulfills the following requirements from the specification:

### Requirement 1.1: Web-based user interface
✅ Provides HTTP-accessible web UI for pool management

### Requirement 1.2: Pool creation and editing
✅ Create, edit, and delete package pools with full configuration

### Requirement 1.3: Endpoint assignment
✅ Assign multiple endpoints to pools with drag-and-drop interface

### Requirement 1.4: Endpoint grouping and management
✅ Group endpoints by pools and move between different pools

### Requirement 1.5: Pool and endpoint status display
✅ Real-time status dashboard showing sync states and health metrics

## Components

### Pages
- `Dashboard.jsx` - Main overview with system metrics
- `PoolsPage.jsx` - Pool management and listing
- `PoolDetailPage.jsx` - Detailed pool view with endpoint assignment
- `EndpointsPage.jsx` - Endpoint management and filtering

### Components
- `Layout.jsx` - Main application layout with navigation
- `EndpointCard.jsx` - Draggable endpoint display component
- `CreatePoolModal.jsx` - Pool creation form
- `EditPoolModal.jsx` - Pool editing form
- `DeleteConfirmModal.jsx` - Confirmation dialog for deletions

### Services
- `api.js` - Centralized API client with error handling