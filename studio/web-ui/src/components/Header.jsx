import { useState, useEffect } from 'react'
import { Bell, CheckCircle, AlertCircle, Loader } from 'lucide-react'

function Header({ currentProject, wsMessages }) {
  const [notifications, setNotifications] = useState([])
  const [showNotifications, setShowNotifications] = useState(false)

  useEffect(() => {
    if (wsMessages.length > 0) {
      const latest = wsMessages[wsMessages.length - 1]
      setNotifications((prev) => [latest, ...prev.slice(0, 4)])
    }
  }, [wsMessages])

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'process_started':
        return <Loader className="w-4 h-4 text-blue-500 animate-spin" />
      case 'process_completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'process_error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <Bell className="w-4 h-4 text-gray-500" />
    }
  }

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <img
            src="/logo_horizontal.svg"
            alt="FableFlow"
            className="h-8"
          />
          <div className="border-l border-gray-300 pl-4">
            {currentProject ? (
              <div>
                <h2 className="text-lg font-semibold text-gray-800">{currentProject.name}</h2>
                <p className="text-sm text-gray-500">
                  {currentProject.versions.length} versions • {currentProject.media.images.length}{' '}
                  images
                </p>
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-semibold text-gray-800">Story Projects</h2>
                <p className="text-sm text-gray-500">Select a project to view versions, media, and content</p>
              </div>
            )}
          </div>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <Bell className="w-5 h-5" />
            {notifications.length > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              <div className="p-3 border-b border-gray-200">
                <h3 className="font-semibold text-gray-800">Notifications</h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-gray-500 text-sm">No notifications</div>
                ) : (
                  notifications.map((notif, index) => (
                    <div key={index} className="p-3 border-b border-gray-100 hover:bg-gray-50">
                      <div className="flex items-start">
                        <div className="mt-0.5">{getNotificationIcon(notif.type)}</div>
                        <div className="ml-3 flex-1">
                          <p className="text-sm text-gray-800">{notif.message}</p>
                          {notif.project && (
                            <p className="text-xs text-gray-500 mt-1">{notif.project}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
