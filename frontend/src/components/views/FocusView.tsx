import { motion } from 'framer-motion';
import { useStore } from '@/state/store';
import { useShallow } from 'zustand/react/shallow';
import { selectActiveNode, selectNodeMessages } from '@/state/selectors';
import { MessageBubble } from '@/components/node/MessageBubble';
import { ChatBar } from '@/components/ui/ChatBar';
import { useRef, useEffect, useState } from 'react';
import { Bot, Sparkles, Loader2 } from 'lucide-react';

// Backend API URL - in non-dev this should be env var, for local assume localhost:8000
// But actually Frontend is 5174/5175, Backend is 8000.
const BACKEND_API = 'http://localhost:8000';

export function FocusView() {
    const activeNode = useStore(selectActiveNode);
    // Use useShallow to key the selector result stability
    const messages = useStore(
        useShallow((state) =>
            activeNode ? selectNodeMessages(state, activeNode.id) : []
        )
    );
    const connect = useStore((state) => state.connect);

    // Local state for the "Start Research" input
    const [topic, setTopic] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleStartResearch = async () => {
        if (!topic.trim()) return;
        setIsLoading(true);

        try {
            // 1. Start SSE connection first to listen for "NODE_CREATED" etc.
            connect(`${BACKEND_API}/api/events`);

            // 2. POST the topic
            const res = await fetch(`${BACKEND_API}/api/research`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });

            if (!res.ok) {
                throw new Error('Failed to start research');
            }
            // Success - the SSE stream should pick up from here and state will update
            // activeNode will eventually become populated by an event.
        } catch (err) {
            console.error(err);
            alert('Failed to start research backend. ensure uvicorn is running.');
            setIsLoading(false);
        }
    };

    if (!activeNode) {
        return (
            <div className="flex flex-col h-full items-center justify-center text-muted-foreground space-y-4 p-8">
                <div className="w-16 h-16 bg-muted/30 rounded-full flex items-center justify-center mb-2">
                    <Bot className="w-8 h-8 opacity-50" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">Deep Research</h3>
                <p className="text-center max-w-sm text-sm mb-4">
                    Enter a research topic to start your session.
                </p>

                <div className="flex w-full max-w-sm items-center space-x-2">
                    <input
                        className="flex-1 bg-background border px-3 py-2 rounded-md ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="e.g. Current state of Quantum Computing..."
                        value={topic}
                        onChange={e => setTopic(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleStartResearch()}
                        disabled={isLoading}
                    />
                    <button
                        className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-md flex items-center gap-2 disabled:opacity-50"
                        onClick={handleStartResearch}
                        disabled={!topic.trim() || isLoading}
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <motion.div
            className="flex flex-col h-full w-full max-w-3xl mx-auto bg-background border-x border-border shadow-sm"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
        >
            <div className="flex items-center justify-between p-4 border-b">
                <div>
                    <h2 className="text-lg font-semibold">{activeNode.data.title || activeNode.data.kind}</h2>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-xs text-muted-foreground">Focus Mode</span>
                    </div>
                </div>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                    <p className="text-muted-foreground text-center mt-10">Start the conversation...</p>
                ) : (
                    messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
                )}
            </div>

            <div className="mt-auto">
                <ChatBar />
            </div>
        </motion.div>
    );
}
