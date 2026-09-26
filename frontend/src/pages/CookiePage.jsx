/**
 * CookiePage — Facebook Connection Gateway
 * Designed specifically for Mobile & Desktop users:
 * 1. OAuth / Facebook App Authorization:
 *    - 1-Click prompt asking user to allow app access.
 *    - If allowed -> connects and goes to Dashboard.
 *    - If denied/cancelled -> shows clear, explicit error message.
 * 2. Direct Facebook Account Login (Email/Phone + Password + 2FA):
 *    - Headless browser connects, fetches profile, establishes session automatically.
 *    - No manual cookie copying required.
 * 3. Optional: Manual Cookie Paste (Collapsible for advanced desktop users).
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ShieldCheck, 
  Smartphone, 
  KeyRound, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  LogOut, 
  Lock,
  Mail,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { 
  signOut,
  FacebookAuthProvider, 
  signInWithPopup 
} from 'firebase/auth';
import { auth } from '../firebase';
import { 
  connectFacebookOAuth, 
  loginFacebookAccount, 
  loginWithCookie 
} from '../api';
import '../styles/CookiePage.css';

const FacebookIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

export default function CookiePage({ onCookieSuccess }) {
  const navigate = useNavigate();

  // Active tab: 'oauth' (Direct FB Auth / App) | 'account' (Email/Phone + Pass)
  const [tab, setTab] = useState('oauth');

  // Account login fields
  const [fbAccount, setFbAccount] = useState('');
  const [fbPassword, setFbPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [fbTwoFactor, setFbTwoFactor] = useState('');
  const [requires2FA, setRequires2FA] = useState(false);

  // Manual Cookie fields (collapsible for PC)
  const [showManualCookie, setShowManualCookie] = useState(false);
  const [manualCookie, setManualCookie] = useState('');

  // Status & loading
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  // ------------------------------------------------------------------
  // 1. Facebook App / OAuth Authorization (Direct 1-Click)
  // ------------------------------------------------------------------
  const handleFacebookOAuth = async () => {
    setLoading(true);
    setStatus({
      type: 'loading',
      message: 'Đang chuyển hướng sang ứng dụng Facebook... Vui lòng chọn "Tiếp tục / Cho phép".'
    });

    const provider = new FacebookAuthProvider();
    provider.addScope('public_profile');
    provider.addScope('email');
    provider.setCustomParameters({
      display: 'popup'
    });

    try {
      const result = await signInWithPopup(auth, provider);
      const user = result.user;
      
      const credential = FacebookAuthProvider.credentialFromResult(result);
      const accessToken = credential?.accessToken || '';
      const fbUid = user.providerData?.[0]?.uid || user.uid;
      const fbName = user.displayName || 'Tài khoản Facebook';

      // Connect Facebook info to backend
      try {
        await connectFacebookOAuth({
          facebookId: fbUid,
          facebookName: fbName,
          accessToken: accessToken
        });
      } catch (beErr) {
        console.warn("Backend session sync note:", beErr);
      }

      setStatus({
        type: 'success',
        message: `✅ Cho phép thành công! Xin chào ${fbName}`
      });

      if (onCookieSuccess) {
        onCookieSuccess({
          userId: fbUid,
          userName: fbName
        });
      }

      setTimeout(() => navigate('/dashboard'), 800);
    } catch (err) {
      console.error("Facebook OAuth Error:", err);
      let errorMsg = '❌ Không thể kết nối với Facebook.';

      if (
        err.code === 'auth/popup-closed-by-user' ||
        err.code === 'auth/cancelled-popup-request' ||
        err.message?.includes('cancelled') ||
        err.message?.includes('closed')
      ) {
        errorMsg = '❌ Bạn đã từ chối cấp quyền truy cập Facebook hoặc hủy đăng nhập. Vui lòng bấm Cho phép để tiếp tục sử dụng công cụ!';
      } else if (err.code === 'auth/popup-blocked') {
        errorMsg = '⚠️ Trình duyệt đã chặn cửa sổ pop-up. Vui lòng bật cho phép mở pop-up Facebook trên trình duyệt!';
      } else if (err.code === 'auth/account-exists-with-different-credential') {
        errorMsg = '⚠️ Email Facebook này đã liên kết với phương thức khác trong hệ thống.';
      } else {
        errorMsg = `❌ Lỗi đăng nhập Facebook: ${err.message || errorMsg}`;
      }

      setStatus({ type: 'error', message: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------------------------
  // 2. Direct Account Login (Email/Phone + Pass + 2FA)
  // ------------------------------------------------------------------
  const handleAccountLogin = async (e) => {
    e.preventDefault();

    const trimmedAccount = fbAccount.trim();
    const trimmedPass = fbPassword.trim();

    if (!trimmedAccount || !trimmedPass) {
      setStatus({ type: 'error', message: 'Vui lòng nhập đầy đủ Email/SĐT và Mật khẩu Facebook.' });
      return;
    }

    setLoading(true);
    setStatus({
      type: 'loading',
      message: 'Hệ thống đang tự động đăng nhập và xác thực tài khoản Facebook...'
    });

    try {
      const res = await loginFacebookAccount(trimmedAccount, trimmedPass, fbTwoFactor.trim());
      const data = res.data;

      if (data.success) {
        setStatus({
          type: 'success',
          message: `🎉 ${data.message || 'Kết nối tài khoản Facebook thành công!'}`
        });

        if (onCookieSuccess) {
          onCookieSuccess({
            userId: data.user_id,
            userName: data.user_name
          });
        }

        setTimeout(() => navigate('/dashboard'), 1000);
      } else if (data.requires_2fa) {
        setRequires2FA(true);
        setStatus({
          type: 'error',
          message: data.message || 'Tài khoản Facebook yêu cầu mã bảo mật 2 lớp (2FA). Vui lòng nhập mã 6 số bên dưới!'
        });
      } else {
        setStatus({
          type: 'error',
          message: data.message || 'Đăng nhập Facebook thất bại. Vui lòng kiểm tra lại thông tin!'
        });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Lỗi kết nối máy chủ Facebook.';
      setStatus({ type: 'error', message: `❌ ${msg}` });
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------------------------
  // 3. Optional Manual Cookie (Hidden / Collapsed)
  // ------------------------------------------------------------------
  const handleManualCookieSubmit = async (e) => {
    e.preventDefault();

    const trimmed = manualCookie.trim();
    if (!trimmed) {
      setStatus({ type: 'error', message: 'Vui lòng dán chuỗi Cookie Facebook.' });
      return;
    }

    setLoading(true);
    setStatus({ type: 'loading', message: 'Đang xác thực Cookie...' });

    try {
      const res = await loginWithCookie(trimmed);
      const data = res.data;

      if (data.success) {
        setStatus({ type: 'success', message: `${data.message}` });
        if (onCookieSuccess) {
          onCookieSuccess({
            userId: data.user_id,
            userName: data.user_name
          });
        }
        setTimeout(() => navigate('/dashboard'), 800);
      } else {
        setStatus({ type: 'error', message: `${data.message}` });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Lỗi nạp Cookie';
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
          background: 'rgba(0, 0, 0, 0.82)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px',
          animation: 'fadeIn 0.25s ease-in-out'
        }}>
          <Loader2 size={68} className="spinner-anim" style={{ 
            color: '#1877F2',
            marginBottom: '20px'
          }} />
          <h2 style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: '#ffffff',
            textAlign: 'center',
            maxWidth: '460px',
            lineHeight: 1.5
          }}>
            {status.message || 'Đang xử lý kết nối Facebook...'}
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '10px' }}>
            Vui lòng đợi trong giây lát...
          </p>
        </div>
      )}

      <div className="cookie-card" style={{ maxWidth: '560px' }}>
        <div className="login-brand">
          <h1>Tools Marketing</h1>
        </div>
        <p className="login-subtitle" style={{ marginBottom: '22px' }}>
          Kết nối tài khoản Facebook để bắt đầu
        </p>

        {/* Tab Selection */}
        <div style={{
          display: 'flex',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.65)',
          padding: '6px',
          borderRadius: '14px',
          marginBottom: '22px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <button
            type="button"
            onClick={() => { setTab('oauth'); setStatus({ type: '', message: '' }); }}
            disabled={loading}
            style={{
              flex: 1,
              padding: '11px 12px',
              borderRadius: '10px',
              border: 'none',
              background: tab === 'oauth' ? '#1877F2' : 'transparent',
              color: tab === 'oauth' ? '#ffffff' : '#94a3b8',
              fontWeight: 700,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s ease',
              boxShadow: tab === 'oauth' ? '0 4px 14px rgba(24, 119, 242, 0.4)' : 'none'
            }}
          >
            <FacebookIcon /> Cho phép qua FB
          </button>

          <button
            type="button"
            onClick={() => { setTab('account'); setStatus({ type: '', message: '' }); }}
            disabled={loading}
            style={{
              flex: 1,
              padding: '11px 12px',
              borderRadius: '10px',
              border: 'none',
              background: tab === 'account' ? '#1877F2' : 'transparent',
              color: tab === 'account' ? '#ffffff' : '#94a3b8',
              fontWeight: 700,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s ease',
              boxShadow: tab === 'account' ? '0 4px 14px rgba(24, 119, 242, 0.4)' : 'none'
            }}
          >
            <Smartphone size={17} /> Đăng nhập tài khoản
          </button>
        </div>

        {/* Status Message / Error / Success notification */}
        {status.message && (
          <div className={`status-message ${status.type}`} style={{
            marginBottom: '20px',
            padding: '14px 16px',
            borderRadius: '12px',
            fontSize: '0.92rem',
            lineHeight: 1.5,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
          }}>
            {status.type === 'loading' && <Loader2 size={18} className="spinner-anim" style={{ flexShrink: 0, marginTop: '2px' }} />}
            {status.type === 'success' && <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#10b981' }} />}
            {status.type === 'error' && <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#f43f5e' }} />}
            <span>{status.message}</span>
          </div>
        )}

        {/* TAB 1: Direct Facebook OAuth / App Authorization */}
        {tab === 'oauth' && (
          <div>
            <div className="guide-box" style={{ 
              borderColor: 'rgba(24, 119, 242, 0.35)', 
              background: 'rgba(24, 119, 242, 0.08)' 
            }}>
              <h3 style={{ color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
                <Sparkles size={17} /> Đăng nhập nhanh bằng ứng dụng Facebook
              </h3>
              <p style={{ margin: 0, fontSize: '0.88rem' }}>
                1. Nhấn nút <strong>"TIẾP TỤC VỚI FACEBOOK"</strong> bên dưới.<br />
                2. Facebook sẽ mở ra và hỏi: <em>"Cho phép tiếp tục với [Tên bạn]?"</em>.<br />
                3. Chọn <strong>"Tiếp tục / Cho phép"</strong> để hoàn tất đăng nhập!
              </p>
            </div>

            <button
              type="button"
              onClick={handleFacebookOAuth}
              disabled={loading}
              style={{
                width: '100%',
                padding: '16px 20px',
                fontSize: '1rem',
                fontWeight: 700,
                color: '#ffffff',
                background: 'linear-gradient(135deg, #1877F2 0%, #0c56bd 100%)',
                border: 'none',
                borderRadius: '14px',
                boxShadow: '0 6px 24px rgba(24, 119, 242, 0.45)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                transition: 'all 0.2s ease',
                marginTop: '10px'
              }}
              onMouseOver={(e) => {
                if (!loading) e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="spinner-anim" /> Đang chuyển sang Facebook...
                </>
              ) : (
                <>
                  <FacebookIcon /> ĐĂNG NHẬP / TIẾP TỤC VỚI FACEBOOK
                </>
              )}
            </button>
          </div>
        )}

        {/* TAB 2: Direct Account Login (Email/Phone + Pass + 2FA) */}
        {tab === 'account' && (
          <form onSubmit={handleAccountLogin}>
            <div className="guide-box" style={{ 
              borderColor: 'rgba(56, 189, 248, 0.3)', 
              background: 'rgba(56, 189, 248, 0.06)' 
            }}>
              <h3 style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
                <ShieldCheck size={17} /> Đăng nhập trực tiếp (Dành cho điện thoại & PC)
              </h3>
              <p style={{ margin: 0, fontSize: '0.86rem' }}>
                Hệ thống tự động đăng nhập và đồng bộ tài khoản để đăng bài. <strong>Không cần thao tác lấy Cookie!</strong>
              </p>
            </div>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '8px' }}>
                <Mail size={15} /> Email hoặc Số điện thoại Facebook
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="Nhập email hoặc SĐT đăng nhập Facebook"
                value={fbAccount}
                onChange={(e) => setFbAccount(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '8px' }}>
                <Lock size={15} /> Mật khẩu Facebook
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="••••••••"
                  value={fbPassword}
                  onChange={(e) => setFbPassword(e.target.value)}
                  disabled={loading}
                  required
                  style={{ paddingRight: '42px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* 2FA Code input - visible if requires2FA or user clicks to show */}
            {(requires2FA || fbTwoFactor) && (
              <div className="form-group" style={{ marginBottom: '16px', animation: 'fadeIn 0.3s ease' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.88rem', color: '#f59e0b', marginBottom: '8px' }}>
                  <KeyRound size={15} /> Mã bảo mật 2 lớp (2FA 6 số)
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Ví dụ: 123456"
                  maxLength={10}
                  value={fbTwoFactor}
                  onChange={(e) => setFbTwoFactor(e.target.value)}
                  disabled={loading}
                  style={{ borderColor: '#f59e0b' }}
                />
                <small style={{ color: '#94a3b8', fontSize: '0.78rem', display: 'block', marginTop: '4px' }}>
                  Lấy mã 6 số từ Google Authenticator hoặc tin nhắn SMS gửi về điện thoại của bạn.
                </small>
              </div>
            )}

            {!requires2FA && !fbTwoFactor && (
              <div style={{ textAlign: 'right', marginBottom: '16px' }}>
                <button
                  type="button"
                  onClick={() => setRequires2FA(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#38bdf8',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textDecoration: 'underline'
                  }}
                >
                  + Tài khoản có bật mã xác thực 2 lớp (2FA)?
                </button>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                width: '100%',
                padding: '15px 20px',
                fontSize: '0.96rem',
                fontWeight: 700,
                borderRadius: '12px'
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner-anim" /> Đang đăng nhập tài khoản...
                </>
              ) : (
                <>
                  <ShieldCheck size={18} /> ĐĂNG NHẬP VÀ KẾT NỐI FACEBOOK
                </>
              )}
            </button>
          </form>
        )}

        {/* Collapsible Manual Cookie Option for PC users */}
        <div style={{ marginTop: '26px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
          <button
            type="button"
            onClick={() => setShowManualCookie(!showManualCookie)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: '0.82rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              width: '100%',
              transition: 'color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.color = '#cbd5e1'}
            onMouseOut={(e) => e.currentTarget.style.color = '#94a3b8'}
          >
            {showManualCookie ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            {showManualCookie ? 'Thu gọn nạp Cookie thủ công' : 'Hoặc nạp Cookie thủ công (Dành cho máy tính PC)'}
          </button>

          {showManualCookie && (
            <form onSubmit={handleManualCookieSubmit} style={{ marginTop: '16px', animation: 'fadeIn 0.3s ease' }}>
              <div className="form-group" style={{ marginBottom: '14px' }}>
                <textarea
                  className="form-input"
                  placeholder="Dán chuỗi Cookie Facebook (c_user=...; xs=...)"
                  rows={3}
                  value={manualCookie}
                  onChange={(e) => setManualCookie(e.target.value)}
                  disabled={loading}
                  style={{ fontSize: '0.84rem' }}
                />
              </div>

              <button
                type="submit"
                className="btn btn-secondary"
                disabled={loading}
                style={{ width: '100%', padding: '12px', fontSize: '0.88rem' }}
              >
                {loading ? <Loader2 size={16} className="spinner-anim" /> : <KeyRound size={16} />}
                XÁC NHẬN COOKIE
              </button>
            </form>
          )}
        </div>

        {/* System Sign out */}
        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <button 
            type="button"
            onClick={handleSystemLogout}
            disabled={loading}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f87171',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.84rem',
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
