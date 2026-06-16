'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import type { QueueView } from '@/lib/types';
import IngestionTab from './tabs/IngestionTab';
import LensTab from './tabs/LensTab';
import ScoreSignalTab from './tabs/ScoreSignalTab';
import SignalQueueTab from './tabs/SignalQueueTab';
import FrameworksTab from './tabs/FrameworksTab';
import StudioConfigTab from './tabs/StudioConfigTab';
import OutputStudioTab from './tabs/OutputStudioTab';
import EngineTab from './tabs/EngineTab';
import styles from './Dashboard.module.css';

const TABS = ['Ingestion', 'Lens', 'Score Signal', 'Signal Queue', 'Frameworks', 'Studio Config', 'Output Studio', 'Config / Engine'];

export default function Dashboard({ authRequired, onLogout }: { authRequired: boolean; onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState(0);
  const [studioSignal, setStudioSignal] = useState<QueueView | null>(null);

  const handleGenerateFromQueue = (signal: QueueView) => {
    setStudioSignal(signal);
    setActiveTab(6);
  };

  const handleLogout = async () => {
    await api.logout();
    onLogout();
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Signal Scout</h1>
          <span className="dim small">market intelligence</span>
        </div>
        {authRequired && <button onClick={handleLogout}>Logout</button>}
      </header>
      <nav className={styles.nav}>
        {TABS.map((tab, i) => (
          <button key={tab} className={`${styles.tab} ${i === activeTab ? styles.tabActive : ''}`} onClick={() => setActiveTab(i)}>
            {tab}
          </button>
        ))}
      </nav>
      <main className={styles.main}>
        {activeTab === 0 && <IngestionTab />}
        {activeTab === 1 && <LensTab />}
        {activeTab === 2 && <ScoreSignalTab />}
        {activeTab === 3 && <SignalQueueTab onGenerate={handleGenerateFromQueue} />}
        {activeTab === 4 && <FrameworksTab />}
        {activeTab === 5 && <StudioConfigTab />}
        {activeTab === 6 && <OutputStudioTab signal={studioSignal} />}
        {activeTab === 7 && <EngineTab />}
      </main>
    </div>
  );
}
