// import { useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useStore } from '@/state/store';
import { FocusView } from '@/components/views/FocusView';
import { ResearchView } from '@/components/views/ResearchView';
import { deepResearchFixture } from '@/services/events/fixtures';

function App() {
  const uiMode = useStore((state) => state.uiMode);
  const processEvent = useStore((state) => state.processEvent);

  // Dev utility to replay fixture
  const runFixture = () => {
    let i = 0;
    const interval = setInterval(() => {
      if (i >= deepResearchFixture.length) {
        clearInterval(interval);
        return;
      }
      processEvent(deepResearchFixture[i]);
      i++;
    }, 800); // 800ms delay between events
  };

  return (
    <div className="h-screen w-screen bg-background text-foreground overflow-hidden relative font-sans">
      <AnimatePresence mode="wait">
        {uiMode === 'focus' ? (
          <FocusView key="focus" />
        ) : (
          <ResearchView key="research" />
        )}
      </AnimatePresence>

      {/* Debug / Dev Controls */}
      <div className="absolute bottom-4 right-4 z-50 flex gap-2">
        <button
          onClick={runFixture}
          className="bg-primary text-primary-foreground text-xs px-3 py-1.5 rounded shadow hover:opacity-90 transition-opacity"
        >
          ▶ Run Fixture
        </button>
        <button
          onClick={() => useStore.getState().reset()}
          className="bg-destructive text-destructive-foreground text-xs px-3 py-1.5 rounded shadow hover:opacity-90 transition-opacity"
        >
          Reset
        </button>
      </div>
    </div>
  );
}

export default App;
