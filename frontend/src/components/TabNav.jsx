/**
 * TabNav Component — Segmented Pill Bar with Lucide Icons
 */

import { Users, Send, History } from 'lucide-react';

export default function TabNav({ activeTab, onTabChange, selectedCount = 0, historyCount = 0 }) {
  const tabs = [
    { key: 'groups', label: 'Danh sách Group', icon: Users, badge: selectedCount > 0 ? selectedCount : null },
    { key: 'post', label: 'Soạn & Đăng bài', icon: Send },
    { key: 'history', label: 'Lịch sử chiến dịch', icon: History, badge: historyCount > 0 ? historyCount : null },
  ];

  return (
    <div className="tab-segmented-bar">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            className={`tab-segmented-btn ${isActive ? 'active' : ''}`}
            onClick={() => onTabChange(tab.key)}
          >
            <Icon size={18} />
            <span>{tab.label}</span>
            {tab.badge !== null && <span className="tab-badge">{tab.badge}</span>}
          </button>
        );
      })}
    </div>
  );
}
