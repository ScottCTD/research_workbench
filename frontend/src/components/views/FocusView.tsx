import { motion } from 'framer-motion';
import { useStore } from '@/state/store';
import { useShallow } from 'zustand/react/shallow';
import { selectActiveNode, selectAgentMessages } from '@/state/selectors';
import { MessageBubble } from '@/components/node/MessageBubble';
import { ChatBar } from '@/components/ui/ChatBar';
import { useRef, useEffect } from 'react';

export function FocusView() {
    const activeNode = useStore(selectActiveNode);
    // Use useShallow to key the selector result stability
    const messages = useStore(
        useShallow((state) =>
            activeNode ? selectAgentMessages(state, activeNode.data.kind) : []
        )
    );
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const title = activeNode?.data.title || 'General Assistant';

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
                    <h2 className="text-lg font-semibold">{title}</h2>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        <span className="text-xs text-muted-foreground">Focus Mode</span>
                    </div>
                </div>
                <button
                    onClick={() => useStore.getState().setUiMode('research')}
                    className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors font-medium"
                >
                    Canvas View
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                    <p className="text-muted-foreground text-center mt-10">Let's do some research!</p>
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
