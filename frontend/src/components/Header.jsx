/**
 * Header Component — Next-Gen Modern SaaS Style
 */

import { Zap, LogOut, ShieldCheck } from 'lucide-react';
import { signOut } from 'firebase/auth';
import { auth } from '../firebase';
import { logoutCookie } from '../api';

export default function Header({ fbUserName, fbUserId, onLogoutFb }) {
  const handleLogout = async () => {
    try {
      await logoutCookie();
    } catch (e) {
      // ignore
    }
    if (onLogoutFb) onLogoutFb();
    await signOut(auth);
  };

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-wrapper">
          <Zap size={22} color="#ffffff" />
        </div>
        <span className="brand-title">Tools Marketing</span>
      </div>

      {fbUserName && (
        <div className="user-status-card">
          <span className="pulse-dot"></span>
          <span>{fbUserName}</span>
          {fbUserId && <span style={{ opacity: 0.7, fontSize: '0.78rem' }}>({fbUserId})</span>}
        </div>
      )}

      <button className="btn-logout-modern" onClick={handleLogout} title="Đăng xuất">
        <LogOut size={16} />
        <span>Đăng xuất</span>
      </button>
    </header>
  );
}
