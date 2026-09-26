/**
 * GroupsTab Component — Redesigned Modern List with Custom Row Selection & Search
 */

import { useState, useEffect, useMemo } from 'react';
import { Search, CheckSquare, Square, RefreshCw, Users, Check, Loader2 } from 'lucide-react';
import { fetchGroups } from '../api';
import '../styles/GroupsTab.css';

export default function GroupsTab({ groups, setGroups, selectedIds, setSelectedIds }) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState({ type: '', message: 'Chưa tải nhóm nào.' });
  const [loading, setLoading] = useState(false);

  const loadGroups = async () => {
    setLoading(true);
    setStatus({ type: 'loading', message: 'Đang kết nối tải danh sách nhóm từ Facebook...' });

    try {
      const res = await fetchGroups();
      const data = res.data;
      if (data.success && data.groups.length > 0) {
        setGroups(data.groups);
        setStatus({
          type: 'success',
          message: `Đã tải ${data.total} nhóm thành công.`,
        });
      } else {
        setGroups([]);
        setStatus({
          type: 'error',
          message: 'Không tìm thấy nhóm nào hoặc Cookie bị lỗi.',
        });
      }
    } catch (err) {
      setStatus({
        type: 'error',
        message: `Lỗi: ${err.response?.data?.detail || err.message}`,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (groups.length === 0) {
      loadGroups();
    }
  }, []);

  const filteredGroups = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return groups;
    return groups.filter((g) => g.name.toLowerCase().includes(q));
  }, [groups, search]);

  const toggleGroup = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    const ids = filteredGroups.map((g) => g.id);
    setSelectedIds((prev) => [...new Set([...prev, ...ids])]);
  };

  const clearAll = () => {
    const visibleIds = new Set(filteredGroups.map((g) => g.id));
    setSelectedIds((prev) => prev.filter((id) => !visibleIds.has(id)));
  };

  return (
    <div className="main-card-panel">
      <div className="panel-header">
        <div className="panel-header-title">
          <Users size={22} />
          <span>Danh sách Nhóm Facebook đã tham gia</span>
        </div>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-sub)', fontWeight: '600' }}>
          Đã chọn <strong style={{ color: 'var(--accent-cyan)' }}>{selectedIds.length}</strong> / {groups.length} Group
        </span>
      </div>

      {/* Search Input */}
      <div className="search-box-wrapper">
        <Search size={18} />
        <input
          type="text"
          className="search-box-input"
          placeholder="Tìm kiếm nhanh tên Group..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Scrollable Group Rows */}
      <div className="groups-scroll-grid">
        {loading && (
          <div className="empty-state-card">
            <Loader2 size={32} className="spinner-anim" />
            <p>Đang tải danh sách nhóm từ Facebook...</p>
          </div>
        )}

        {!loading && filteredGroups.length === 0 && (
          <div className="empty-state-card">
            <Users size={36} />
            <p>Không tìm thấy nhóm nào hợp lệ</p>
          </div>
        )}

        {!loading &&
          filteredGroups.map((group) => {
            const isSelected = selectedIds.includes(group.id);
            return (
              <div
                key={group.id}
                className={`group-row ${isSelected ? 'selected' : ''}`}
                onClick={() => toggleGroup(group.id)}
              >
                <div className="custom-checkbox">
                  {isSelected && <Check size={14} strokeWidth={3} />}
                </div>
                <span className="group-name-text">{group.name}</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>
                  ID: {group.id}
                </span>
              </div>
            );
          })}
      </div>

      {/* Actions Toolbar */}
      <div className="actions-toolbar">
        <span className="status-indicator-text">{status.message}</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-chip" onClick={selectAll} disabled={loading}>
            <CheckSquare size={16} /> Chọn tất cả
          </button>
          <button className="btn-chip" onClick={clearAll} disabled={loading}>
            <Square size={16} /> Bỏ chọn
          </button>
          <button className="btn-chip" onClick={loadGroups} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spinner-anim' : ''} /> Tải lại
          </button>
        </div>
      </div>
    </div>
  );
}
