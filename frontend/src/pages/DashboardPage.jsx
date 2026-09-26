/**
 * DashboardPage Component — High-End Modern Container
 */

import { useState } from 'react';
import Header from '../components/Header';
import TabNav from '../components/TabNav';
import GroupsTab from './GroupsTab';
import PostTab from './PostTab';
import HistoryTab from './HistoryTab';
import '../styles/Dashboard.css';

export default function DashboardPage({ fbUserName, fbUserId, onLogoutFb }) {
  const [activeTab, setActiveTab] = useState('groups');
  const [groups, setGroups] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);

  const handleCampaignStarted = () => {
    setActiveTab('history');
  };

  return (
    <div className="dashboard-wrapper">
      <div className="dashboard-container">
        <Header
          fbUserName={fbUserName}
          fbUserId={fbUserId}
          onLogoutFb={onLogoutFb}
        />

        <TabNav
          activeTab={activeTab}
          onTabChange={setActiveTab}
          selectedCount={selectedIds.length}
        />

        {activeTab === 'groups' && (
          <GroupsTab
            groups={groups}
            setGroups={setGroups}
            selectedIds={selectedIds}
            setSelectedIds={setSelectedIds}
          />
        )}

        {activeTab === 'post' && (
          <PostTab
            groups={groups}
            selectedIds={selectedIds}
            onCampaignStarted={handleCampaignStarted}
          />
        )}

        {activeTab === 'history' && <HistoryTab />}
      </div>
    </div>
  );
}
