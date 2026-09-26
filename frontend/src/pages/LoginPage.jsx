/**
 * LoginPage — Modern Glassmorphism Auth with Facebook OAuth & Email/Password
 */

import { useState } from 'react';
import { Mail, Lock, Loader2, CheckCircle2, AlertTriangle, UserPlus, LogIn } from 'lucide-react';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword 
} from 'firebase/auth';
import { auth } from '../firebase';
import '../styles/LoginPage.css';

export default function LoginPage({ onLoginSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

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
