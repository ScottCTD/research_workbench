import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { type AppState, initialState, applyEvent } from './reducers';
import type { ServerEvent } from '@/types/events';
import { SseClient } from '@/services/events/SseClient';

const BACKEND_API = 'http://localhost:8000';

type StoreActions = {
    processEvent: (event: ServerEvent) => void;
    setActiveNode: (id: string) => void;
    setSelectedNode: (id: string | null) => void;
    setUiMode: (mode: 'focus' | 'research') => void;
    reset: () => void;
    clearConversation: () => void;
    connect: (url: string) => void;
    startResearch: (topic: string) => Promise<void>;
    sendMessage: (content: string) => Promise<void>;
};

// Singleton client - simple approach for now
let sseClient: SseClient | null = null;
let sseUrl: string | null = null;

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
        clearConversation: () =>
            set((state) => {
                const clearedNodeMessageIds: Record<string, string[]> = {};
                for (const nodeId of Object.keys(state.nodes)) {
                    clearedNodeMessageIds[nodeId] = [];
                }
                return {
                    messages: {},
                    nodeMessageIds: clearedNodeMessageIds,
                };
            }),

        connect: (url) => {
            if (sseClient && sseUrl === url) {
                sseClient.connect();
                return;
            }
            if (sseClient) {
                sseClient.disconnect();
            }
            sseClient = new SseClient(url, (event) => {
                get().processEvent(event);
            });
            sseUrl = url;
            sseClient.connect();
        },

        startResearch: async (topic: string) => {
            if (!topic.trim()) return;
            get().connect(`${BACKEND_API}/api/events`);
            try {
                const res = await fetch(`${BACKEND_API}/api/research`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic }),
                });
                if (!res.ok) {
                    throw new Error('Failed to start research');
                }
            } catch (error) {
                console.error('Failed to start research:', error);
            }
        },

        sendMessage: async (content: string) => {
            // Optimistic update could go here, but we rely on backend echo
            const message = content.trim();
            if (!message) return;
            get().connect(`${BACKEND_API}/api/events`);
            try {
                const res = await fetch(`${BACKEND_API}/api/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message }),
                });
                let payload: { status?: string } | null = null;
                try {
                    payload = await res.json();
                } catch {
                    payload = null;
                }
                if (!res.ok || payload?.status === 'error') {
                    await get().startResearch(message);
                }
            } catch (error) {
                console.error('Failed to send message:', error);
            }
        },
    }))
);
