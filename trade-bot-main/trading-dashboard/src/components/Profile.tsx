import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { userAPI, authAPI } from '../services/api'

export const Profile = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      // Load user profile from backend if auth is enabled
      if (user.token !== 'no-auth-required') {
        loadUserProfile();
      } else {
        // For anonymous access mode, use username as name
        setFullName(user.username.charAt(0).toUpperCase() + user.username.slice(1));
        setEmail(`${user.username}@example.com`);
      }
    }
  }, [user])

  const loadUserProfile = async () => {
    try {
      const response = await userAPI.getSettings();
      if (response.settings) {
        setFullName(response.settings.fullName || user?.username || '');
        setEmail(response.settings.email || `${user?.username || 'user'}@example.com`);
      }
    } catch (err) {
      // If settings API is not available, use default values
      setFullName(user?.username || '');
      setEmail(`${user?.username || 'user'}@example.com`);
      console.warn('Could not load user settings, using defaults', err);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      // Update profile via backend API
      const profileData = {
        fullName,
        email,
        username: user?.username
      };

      // Save settings to backend
      const response = await userAPI.saveSettings(profileData);
      
      if (response.success) {
        setSuccess('Profile updated successfully!');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        throw new Error(response.message || 'Failed to update profile');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <p className="text-slate-400">Please log in to view your profile</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br p-4 md:p-8 from-slate-50 to-blue-50">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 text-slate-900">User Profile</h1>
          <p className="text-slate-600 dark:text-slate-400">Manage your account settings and preferences</p>
        </div>
        <div className="rounded-2xl shadow-lg overflow-hidden bg-white">
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-8 text-white">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-user w-8 h-8" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
              </div>
              <div>
                <h2 className="text-2xl font-bold">{fullName || user.username}</h2>
                <p className="text-blue-100">Connected Account</p>
              </div>
            </div>
          </div>
          <div className="p-8 space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            {success && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 mb-6">
                <p className="text-green-400 text-sm">{success}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <div className="flex items-center gap-2 mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-user w-4 h-4" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>Username
                </div>
              </label>
              <div className="bg-slate-100 dark:bg-slate-700 rounded-lg p-4 text-slate-900 dark:text-slate-100 font-medium">
                {user.username}
              </div>
            </div>
            
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  <div className="flex items-center gap-2 mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-user w-4 h-4" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>Full Name
                  </div>
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  className="w-full px-4 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  <div className="flex items-center gap-2 mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-mail w-4 h-4" aria-hidden="true"><path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"></path><rect x="2" y="4" width="20" height="16" rx="2"></rect></svg>Email Address
                  </div>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  className="w-full px-4 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold rounded-lg transition-colors"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>

            <div className="bg-blue-50 dark:bg-slate-700/50 rounded-lg p-4 border border-blue-200 dark:border-slate-600">
              <p className="text-sm text-slate-700 dark:text-slate-300"><span className="font-semibold">Account Status:</span> Active</p>
              <p className="text-sm text-slate-700 dark:text-slate-300 mt-2"><span className="font-semibold">Login Method:</span> Email &amp; Password</p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">Trading Preferences</h3>
              <div className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                <p>• Risk Assessment: Enabled</p>
                <p>• Stop-Loss Alerts: Enabled</p>
                <p>• Trade Confirmations: Required</p>
              </div>
            </div>
            
            <div className="pt-6 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={async () => {
                  try {
                    // Call backend logout endpoint
                    await authAPI.logout();
                    // Clear local auth state
                    logout();
                    // Navigate to login page
                    navigate('/login');
                  } catch (err) {
                    // Even if backend call fails, still logout locally
                    logout();
                    navigate('/login');
                  }
                }}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-500 hover:bg-red-600 disabled:bg-red-300 text-white font-semibold rounded-lg transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-log-out w-5 h-5" aria-hidden="true"><path d="m16 17 5-5-5-5"></path><path d="M21 12H9"></path><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path></svg>
                Logout
              </button>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 text-center">This will clear your session and log you out from all devices.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}