/**
 * CookiePage — Modern Facebook Login & Cookie Setup
 * Supports:
 * 1. Automatic login via interactive browser popup (Playwright)
 * 2. Manual Cookie string pasting
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Cookie, 
  KeyRound, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  LogOut, 
  Globe, 
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { signOut } from 'firebase/auth';
import { auth } from '../firebase';
import { loginWithCookie, loginWithBrowser } from '../api';
import '../styles/CookiePage.css';

export default function CookiePage({ onCookieSuccess }) {
  const navigate = useNavigate();

  const [authMethod, setAuthMethod] = useState('browser'); // 'browser' | 'cookie'
  const [cookie, setCookie] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  // Handle manual cookie submission
  const handleCookieLogin = async (e) => {
    e.preventDefault();

    const trimmed = cookie.trim();
    if (!trimmed) {
      setStatus({ type: 'error', message: 'Vui lòng nhập chuỗi Cookie Facebook.' });
      return;
    }

    setLoading(true);
    setStatus({ type: 'loading', message: 'Đang kết nối & xác thực Cookie với Facebook...' });

    try {
      const res = await loginWithCookie(trimmed);
      const data = res.data;

      if (data.success) {
        setStatus({ type: 'success', message: `${data.message}` });
        if (onCookieSuccess) {
          onCookieSuccess({
            userId: data.user_id,
            userName: data.user_name,
          });
        }
        setTimeout(() => navigate('/dashboard'), 800);
      } else {
        setStatus({ type: 'error', message: `${data.message}` });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Lỗi kết nối server';
      setStatus({ type: 'error', message: `${msg}` });
    } finally {
      setLoading(false);
    }
  };

  // Handle automatic browser login
  const handleBrowserLogin = async () => {
    setLoading(true);
    setStatus({ 
      type: 'loading', 
      message: 'Đang khởi chạy trình duyệt Facebook... Vui lòng đăng nhập tài khoản trên cửa sổ vừa mở.' 
    });

    try {
      const res = await loginWithBrowser();
      const data = res.data;

      if (data.success) {
        setStatus({ type: 'success', message: `🎉 ${data.message}` });
        if (onCookieSuccess) {
          onCookieSuccess({
            userId: data.user_id,
            userName: data.user_name,
          });
        }
        setTimeout(() => navigate('/dashboard'), 1000);
      } else {
        setStatus({ type: 'error', message: `${data.message}` });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Lỗi kết nối với trình duyệt tự động';
      setStatus({ type: 'error', message: `${msg}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSystemLogout = async () => {
    try {
      await signOut(auth);
      navigate('/login');
    } catch (e) {
      console.error("Error signing out:", e);
    }
  };

  return (
    <div className="cookie-page">
      {/* Loading Overlay */}
      {loading && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          animation: 'fadeIn 0.3s ease-in-out'
        }}>
          <div style={{
            textAlign: 'center',
            color: 'white'
          }}>
            <div style={{
              marginBottom: '24px'
            }}>
              <Loader2 size={80} className="spinner-anim" style={{ 
                color: '#3b82f6',
                animation: 'spin 1s linear infinite'
              }} />
            </div>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              marginBottom: '12px'
            }}>
              {status.message ? status.message : 'Đang xử lý...'}
            </h2>
            {authMethod === 'browser' && (
              <p style={{
                fontSize: '0.95rem',
                color: '#cbd5e1',
                marginTop: '12px',
                maxWidth: '400px'
              }}>
                💡 Vui lòng chờ trình duyệt mở ra. Nếu không mở được, vui lòng kiểm tra firewall hoặc cài đặt bảo mật.
              </p>
            )}
          </div>
        </div>
      )}

      <div className="cookie-card" style={{ maxWidth: '580px' }}>
        <div className="login-brand">
          <h1>Tools Marketing</h1>
        </div>
        <p className="login-subtitle">Kết nối tài khoản Facebook của bạn</p>

        {/* Method Switcher Tabs */}
        <div style={{
          display: 'flex',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.6)',
          padding: '5px',
          borderRadius: '12px',
          marginBottom: '20px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <button
            type="button"
            onClick={() => { setAuthMethod('browser'); setStatus({ type: '', message: '' }); }}
            disabled={loading}
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              background: authMethod === 'browser' ? 'var(--accent-blue, #3b82f6)' : 'transparent',
              color: authMethod === 'browser' ? '#ffffff' : '#94a3b8',
              fontWeight: 700,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
          >
            <Globe size={16} /> Đăng nhập bằng Facebook
          </button>
          
          <button
            type="button"
            onClick={() => { setAuthMethod('cookie'); setStatus({ type: '', message: '' }); }}
            disabled={loading}
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              background: authMethod === 'cookie' ? 'var(--accent-blue, #3b82f6)' : 'transparent',
              color: authMethod === 'cookie' ? '#ffffff' : '#94a3b8',
              fontWeight: 700,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
          >
            <Cookie size={16} /> Dán chuỗi Cookie
          </button>
        </div>

        {/* Method 1: Interactive Browser Login */}
        {authMethod === 'browser' && (
          <div>
            <div className="guide-box" style={{ borderColor: 'rgba(59, 130, 246, 0.3)', background: 'rgba(30, 58, 138, 0.15)' }}>
              <h3 style={{ color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={16} /> Đăng nhập Facebook tự động 1-Click
              </h3>
              <p>
                1. Nhấn nút <strong>"Mở trình duyệt đăng nhập Facebook"</strong> bên dưới.<br />
                2. Nhập Email, Mật khẩu & mã 2FA trên cửa sổ Facebook vừa hiện ra.<br />
                3. Sau khi bạn đăng nhập thành công, hệ thống sẽ <strong>tự động lấy Cookie</strong> và chuyển thẳng vào Dashboard!
              </p>
            </div>

            {status.message && (
              <div className={`status-message ${status.type}`} style={{ marginBottom: '16px' }}>
                {status.type === 'loading' && <Loader2 size={16} className="spinner-anim" style={{ display: 'inline', marginRight: '6px' }} />}
                {status.type === 'success' && <CheckCircle2 size={16} style={{ display: 'inline', marginRight: '6px' }} />}
                {status.type === 'error' && <AlertTriangle size={16} style={{ display: 'inline', marginRight: '6px' }} />}
                {status.message}
              </div>
            )}

            <button
              type="button"
              onClick={handleBrowserLogin}
              className="btn btn-primary"
              disabled={loading}
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '1rem',
                background: 'linear-gradient(135deg, #1877F2 0%, #0052cc 100%)',
                boxShadow: '0 4px 20px rgba(24, 119, 242, 0.4)'
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="spinner-anim" /> Đang đợi bạn đăng nhập Facebook...
                </>
              ) : (
                <>
                  <ExternalLink size={20} /> MỞ TRÌNH DUYỆT ĐĂNG NHẬP FACEBOOK
                </>
              )}
            </button>
          </div>
        )}

        {/* Method 2: Manual Cookie input */}
        {authMethod === 'cookie' && (
          <form onSubmit={handleCookieLogin}>
            <div className="guide-box">
              <h3>📌 Hướng dẫn nạp Cookie thủ công</h3>
              <p>
                1. Mở trình duyệt (Chrome/Edge) và đăng nhập Facebook.<br />
                2. Nhấn phím <strong>F12</strong> → chọn Tab <strong>Application</strong> → <strong>Cookies</strong> → <strong>facebook.com</strong>.<br />
                3. Tìm và sao chép chuỗi Cookie (chứa <code>c_user</code> và <code>xs</code>).<br />
                4. Dán chuỗi vào khung bên dưới và bấm nút <strong>Kết nối Cookie</strong>.
              </p>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Cookie size={16} /> Chuỗi Cookie Facebook
              </label>
              <textarea
                className="form-input"
                placeholder="Dán chuỗi cookie (c_user=xxx; xs=yyy; ...)"
                rows={4}
                value={cookie}
                onChange={(e) => setCookie(e.target.value)}
                disabled={loading}
              />
            </div>

            {status.message && (
              <div className={`status-message ${status.type}`}>
                {status.type === 'loading' && <Loader2 size={16} className="spinner-anim" style={{ display: 'inline', marginRight: '6px' }} />}
                {status.type === 'success' && <CheckCircle2 size={16} style={{ display: 'inline', marginRight: '6px' }} />}
                {status.type === 'error' && <AlertTriangle size={16} style={{ display: 'inline', marginRight: '6px' }} />}
                {status.message}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ marginTop: '16px' }}
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="spinner-anim" /> Đang xác thực Facebook...
                </>
              ) : (
                <>
                  <KeyRound size={20} /> KẾT NỐI COOKIE FACEBOOK
                </>
              )}
            </button>
          </form>
        )}

        {/* System Sign out */}
        <div className="auth-switch" style={{ marginTop: '24px', textAlign: 'center' }}>
          <button 
            type="button"
            onClick={handleSystemLogout}
            disabled={loading}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ef4444',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              padding: '6px 12px',
              borderRadius: '6px',
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <LogOut size={14} /> Đăng xuất tài khoản hệ thống
          </button>
        </div>
      </div>
    </div>
  );
}
