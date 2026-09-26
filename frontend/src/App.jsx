/**
 * App — Root Application Component
 * 
 * Manages Firebase auth state and routing.
 * Flow: Email/Password Login -> Cookie setup (if needed) -> Dashboard
 */

import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from './firebase';
import { getCookieStatus } from './api';

import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import CookiePage from './pages/CookiePage';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fbInfo, setFbInfo] = useState({ userName: '', userId: '' });
  const [checkingCookie, setCheckingCookie] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        setCheckingCookie(true);
        try {
          const res = await getCookieStatus();
          if (res.data.logged_in) {
            setFbInfo({
              userId: res.data.user_id,
              userName: res.data.user_name,
            });
          } else {
            setFbInfo({ userName: '', userId: '' });
          }
        } catch (e) {
          console.error("Error checking cookie status:", e);
        } finally {
          setCheckingCookie(false);
        }
      } else {
        setFbInfo({ userName: '', userId: '' });
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleLoginSuccess = async () => {
    // When Firebase login is successful, check cookie status
    setCheckingCookie(true);
    try {
      const res = await getCookieStatus();
      if (res.data.logged_in) {
        setFbInfo({
          userId: res.data.user_id,
          userName: res.data.user_name,
        });
      } else {
        setFbInfo({ userName: '', userId: '' });
      }
    } catch (e) {
      console.error("Error fetching cookie status:", e);
    } finally {
      setCheckingCookie(false);
    }
  };

  const handleCookieSuccess = ({ userId, userName }) => {
    setFbInfo({ userId, userName });
  };

  const handleLogoutFb = () => {
    setFbInfo({ userName: '', userId: '' });
  };

  if (loading || checkingCookie) {
    return (
      <div className="loading-overlay">
        <div className="spinner spinner-lg"></div>
        <span style={{ marginTop: '12px', color: '#94a3b8', fontWeight: 600 }}>Đang kiểm tra phiên làm việc...</span>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Root path — always redirect to login first */}
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />

        {/* Login Page */}
        <Route
          path="/login"
          element={
            user ? (
              fbInfo.userId ? <Navigate to="/dashboard" replace /> : <Navigate to="/cookie" replace />
            ) : (
              <LoginPage onLoginSuccess={handleLoginSuccess} />
            )
          }
        />

        {/* Cookie Page — requires Firebase Auth */}
        <Route
          path="/cookie"
          element={
            <ProtectedRoute user={user} loading={loading}>
              {fbInfo.userId ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <CookiePage onCookieSuccess={handleCookieSuccess} />
              )}
            </ProtectedRoute>
          }
        />

        {/* Dashboard — requires Firebase auth + FB cookie */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute user={user} loading={loading}>
              {!fbInfo.userId ? (
                <Navigate to="/cookie" replace />
              ) : (
                <DashboardPage
                  fbUserName={fbInfo.userName}
                  fbUserId={fbInfo.userId}
                  onLogoutFb={handleLogoutFb}
                />
              )}
            </ProtectedRoute>
          }
        />

        {/* Default redirect */}
        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
