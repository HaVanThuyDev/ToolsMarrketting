/**
 * ProtectedRoute Component
 * 
 * Wraps routes that require Firebase authentication.
 * Redirects to /login if user is not authenticated.
 */

import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ user, loading, children }) {
  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner spinner-lg"></div>
        <span>Đang tải...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
