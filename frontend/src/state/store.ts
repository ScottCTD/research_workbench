import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { type AppState, initialState, applyEvent } from './reducers';
import type { ServerEvent } from '@/types/events';
import { SseClient } from '@/services/events/SseClient';

type StoreActions = {
    processEvent: (event: ServerEvent) => void;
    setActiveNode: (id: string) => void;
    setSelectedNode: (id: string | null) => void;
    setUiMode: (mode: 'focus' | 'research') => void;
    reset: () => void;
    connect: (url: string) => void;
    sendMessage: (content: string) => Promise<void>;
};

// Singleton client - simple approach for now
let sseClient: SseClient | null = null;

export const useStore = create<AppState & StoreActions>()(
    devtools((set, get) => ({
        ...initialState,

        processEvent: (event) =>
            set((state) => {
                const changes = applyEvent(state, event);
                return { ...state, ...changes };
            }),

        setActiveNode: (id) => set({ activeNodeId: id }),
        setSelectedNode: (id) => set({ selectedNodeId: id }),
        setUiMode: (mode) => set({ uiMode: mode }),
        reset: () => set(initialState),

        connect: (url) => {
            if (sseClient) {
                sseClient.disconnect();
            }
            sseClient = new SseClient(url, (event) => {
                get().processEvent(event);
            });
            sseClient.connect();
        },

        sendMessage: async (content: string) => {
            // Optimistic update could go here, but we rely on backend echo
            try {
                await fetch('http://localhost:8000/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: content }),
                });
            } catch (error) {
                console.error('Failed to send message:', error);
            }
        },
    }))
);
