import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Protects routes so only authenticated users (real JWT, not anonymous) can access.
 * Redirects to welcome/login if not authenticated.
 */
export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();

  const hasValidAuth = isAuthenticated && user?.token && user.token !== 'no-auth-required';

  if (!hasValidAuth) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
