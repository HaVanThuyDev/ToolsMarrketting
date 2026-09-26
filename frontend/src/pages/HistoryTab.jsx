/**
 * HistoryTab Component — Redesigned Modern Data Table with Live Status Badges
 */

import { useState, useEffect, useRef } from 'react';
import {
  History,
  ExternalLink,
  Trash2,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  FileSpreadsheet
} from 'lucide-react';
import {
  getCampaignStatus,
  getCampaignHistory,
  deleteCampaignHistory,
  exportCampaignExcel,
} from '../api';
import '../styles/HistoryTab.css';

export default function HistoryTab() {
  const [items, setItems] = useState([]);
  const [inProgress, setInProgress] = useState(false);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  useEffect(() => {
    loadHistory();
    return () => clearInterval(pollRef.current);
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const statusRes = await getCampaignStatus();
      const statusData = statusRes.data;

      if (statusData.in_progress && statusData.items?.length > 0) {
        setItems(statusData.items);
        setInProgress(true);
        startPolling();
      } else {
        const historyRes = await getCampaignHistory();
        setItems(historyRes.data.history || []);
        setInProgress(false);
      }
    } catch (err) {
      console.error('Error loading history:', err);
    } finally {
      setLoading(false);
    }
  };

  const startPolling = () => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await getCampaignStatus();
        const data = res.data;
        if (data.items?.length > 0) {
          setItems(data.items);
        }
        if (!data.in_progress) {
          setInProgress(false);
          clearInterval(pollRef.current);
          const historyRes = await getCampaignHistory();
          setItems(historyRes.data.history || []);
        }
      } catch (err) {
        // ignore
      }
    }, 2000);
  };

  const handleClear = async () => {
    if (inProgress) {
      alert('Không thể xóa lịch sử khi chiến dịch đang chạy!');
      return;
    }
    if (items.length === 0) {
      alert('Lịch sử chiến dịch hiện tại đang trống.');
      return;
    }

    const confirmed = window.confirm(
      'Xác nhận xóa toàn bộ lịch sử kết quả chiến dịch đăng bài?'
    );
    if (!confirmed) return;

    try {
      await deleteCampaignHistory();
      setItems([]);
    } catch (err) {
      alert('Lỗi xóa lịch sử: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleExport = async () => {
    if (items.length === 0) {
      alert('Chưa có dữ liệu lịch sử đăng bài.');
      return;
    }

    try {
      const res = await exportCampaignExcel();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'facebook_marketing_results.xlsx';
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Lỗi xuất Excel: ' + (err.response?.data?.detail || err.message));
    }
  };

  const renderStatusBadge = (statusStr = '') => {
    if (statusStr.includes('Thành công')) {
      return (
        <span className="status-badge-pill success">
          <CheckCircle2 size={14} /> {statusStr}
        </span>
      );
    }
    if (statusStr.includes('Thất bại') || statusStr.includes('Lỗi') || statusStr.includes('❌')) {
      return (
        <span className="status-badge-pill error">
          <XCircle size={14} /> {statusStr}
        </span>
      );
    }
    return (
      <span className="status-badge-pill pending">
        <Clock size={14} className={inProgress ? 'spinner-anim' : ''} /> {statusStr}
      </span>
    );
  };

  return (
    <div className="main-card-panel">
      <div className="panel-header">
        <div className="panel-header-title">
          <History size={22} />
          <span>Báo cáo Lịch sử Đăng bài Marketing</span>
          {inProgress && (
            <span style={{ fontSize: '0.8rem', color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
              <Loader2 size={16} className="spinner-anim" /> Đang chạy chiến dịch...
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-chip" onClick={handleClear} disabled={inProgress}>
            <Trash2 size={15} color="var(--accent-rose)" /> Xóa lịch sử
          </button>
          <button className="btn-chip" onClick={handleExport}>
            <FileSpreadsheet size={15} color="var(--accent-emerald)" /> Xuất Báo cáo Excel
          </button>
        </div>
      </div>

      {loading ? (
        <div className="empty-state-card">
          <Loader2 size={36} className="spinner-anim" />
          <p>Đang tải dữ liệu lịch sử chiến dịch...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state-card">
          <History size={40} />
          <p>Chưa có lịch sử kết quả chiến dịch nào</p>
        </div>
      ) : (
        <div className="modern-table-container">
          <table className="modern-table">
            <thead>
              <tr>
                <th style={{ width: '22%' }}>Nhóm Facebook</th>
                <th style={{ width: '38%' }}>Nội dung bài viết</th>
                <th style={{ width: '16%' }}>Thời gian</th>
                <th style={{ width: '14%' }}>Trạng thái</th>
                <th style={{ width: '10%' }}>Liên kết</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const groupName = item.group || item.Group || 'Group';
                const contentText = item.content || item['Nội dung'] || '';
                const timeText = item.time || item['Thời gian'] || '';
                const statusText = item.status || item['Trạng thái'] || '';
                const postUrl = item.postUrl || item['Link bài đăng'] || '';

                return (
                  <tr key={item.id || idx}>
                    <td style={{ fontWeight: '600', color: 'var(--text-highlight)' }}>{groupName}</td>
                    <td style={{ maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={contentText}>
                      {contentText}
                    </td>
                    <td style={{ color: 'var(--text-sub)', fontSize: '0.82rem', fontFamily: 'JetBrains Mono' }}>{timeText}</td>
                    <td>{renderStatusBadge(statusText)}</td>
                    <td>
                      {postUrl ? (
                        <a href={postUrl} target="_blank" rel="noopener noreferrer" className="link-external-btn">
                          <span>Xem</span> <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
