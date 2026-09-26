/**
 * LoginPage — Modern Glassmorphism Auth with Facebook OAuth & Email/Password
 */

import { useState } from 'react';
import { Mail, Lock, Loader2, CheckCircle2, AlertTriangle, UserPlus, LogIn } from 'lucide-react';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  FacebookAuthProvider, 
  signInWithPopup 
} from 'firebase/auth';
import { auth } from '../firebase';
import '../styles/LoginPage.css';

const FacebookIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

export default function LoginPage({ onLoginSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  // Facebook OAuth Login
  const handleFacebookLogin = async () => {
    setLoading(true);
    setStatus({ 
      type: 'loading', 
      message: 'Đang chuyển hướng sang Facebook... Vui lòng xác nhận cho phép.' 
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
      setStatus({ 
        type: 'success', 
        message: `Đăng nhập Facebook thành công! Xin chào ${user.displayName || 'bạn'}` 
      });

      if (onLoginSuccess) {
        await onLoginSuccess();
      }
    } catch (err) {
      console.error("Facebook Login Error:", err);
      let friendlyMessage = 'Đăng nhập Facebook thất bại.';
      
      if (err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
        friendlyMessage = '❌ Bạn đã hủy đăng nhập Facebook hoặc từ chối cấp quyền truy cập.';
      } else if (err.code === 'auth/account-exists-with-different-credential') {
        friendlyMessage = '⚠️ Email này đã được đăng ký bằng phương thức khác. Vui lòng đăng nhập bằng Email.';
      } else if (err.code === 'auth/operation-not-allowed') {
        friendlyMessage = '⚠️ Đăng nhập Facebook chưa được kích hoạt trong Firebase Console. Vui lòng bật Facebook provider.';
      } else if (err.code === 'auth/popup-blocked') {
        friendlyMessage = '⚠️ Trình duyệt đã chặn cửa sổ pop-up. Vui lòng bật cho phép mở pop-up Facebook trên trình duyệt.';
      } else {
        friendlyMessage = `❌ Đăng nhập thất bại: ${err.message || friendlyMessage}`;
      }

      setStatus({ type: 'error', message: friendlyMessage });
    } finally {
      setLoading(false);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();

    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setStatus({ type: 'error', message: 'Vui lòng điền đầy đủ Email và Mật khẩu.' });
      return;
    }

    if (trimmedPassword.length < 6) {
      setStatus({ type: 'error', message: 'Mật khẩu phải chứa ít nhất 6 ký tự.' });
      return;
    }

    setLoading(true);
    setStatus({ 
      type: 'loading', 
      message: isSignUp ? 'Đang tạo tài khoản mới...' : 'Đang đăng nhập vào hệ thống...' 
    });

    try {
      if (isSignUp) {
        await createUserWithEmailAndPassword(auth, trimmedEmail, trimmedPassword);
        setStatus({ type: 'success', message: 'Tạo tài khoản thành công!' });
      } else {
        await signInWithEmailAndPassword(auth, trimmedEmail, trimmedPassword);
        setStatus({ type: 'success', message: 'Đăng nhập thành công!' });
      }

      if (onLoginSuccess) {
        await onLoginSuccess();
      }
    } catch (err) {
      let friendlyMessage = 'Lỗi xác thực hệ thống.';
      switch (err.code) {
        case 'auth/invalid-credential':
          friendlyMessage = 'Tài khoản hoặc mật khẩu không chính xác.';
          break;
        case 'auth/user-not-found':
          friendlyMessage = 'Email này chưa được đăng ký tài khoản.';
          break;
        case 'auth/wrong-password':
          friendlyMessage = 'Mật khẩu không chính xác.';
          break;
        case 'auth/email-already-in-use':
          friendlyMessage = 'Email này đã được sử dụng bởi tài khoản khác.';
          break;
        case 'auth/invalid-email':
          friendlyMessage = 'Địa chỉ Email không hợp lệ.';
          break;
        default:
          friendlyMessage = err.message || friendlyMessage;
      }
      setStatus({ type: 'error', message: friendlyMessage });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <h1>Tools Marketing</h1>
        </div>
        <p className="login-subtitle">
          Hệ thống tự động hóa Marketing Facebook
        </p>

        {/* Facebook 1-Click Login Button */}
        <button
          type="button"
          className="btn-facebook"
          onClick={handleFacebookLogin}
          disabled={loading}
        >
          {loading && status.type === 'loading' ? (
            <>
              <Loader2 size={20} className="spinner-anim" /> Đang chuyển sang Facebook...
            </>
          ) : (
            <>
              <FacebookIcon /> ĐĂNG NHẬP BẰNG FACEBOOK
            </>
          )}
        </button>

        <div className="auth-divider">
          <span>Hoặc dùng tài khoản Email</span>
        </div>

        <form onSubmit={handleAuth}>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Mail size={16} /> Địa chỉ Email
            </label>
            <input
              type="email"
              className="form-input"
              placeholder="nhap-email@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={16} /> Mật khẩu
            </label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
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
                <Loader2 size={20} className="spinner-anim" /> Vui lòng chờ...
              </>
            ) : isSignUp ? (
              <>
                <UserPlus size={20} /> ĐĂNG KÝ EMAIL
              </>
            ) : (
              <>
                <LogIn size={20} /> ĐĂNG NHẬP EMAIL
              </>
            )}
          </button>
        </form>

        <div className="auth-switch">
          <span>
            {isSignUp ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}
            {' '}
            <a onClick={() => {
              if (!loading) {
                setIsSignUp(!isSignUp);
                setStatus({ type: '', message: '' });
              }
            }}>
              {isSignUp ? 'Đăng nhập tại đây' : 'Đăng ký nhanh'}
            </a>
          </span>
        </div>
      </div>
    </div>
  );
}
