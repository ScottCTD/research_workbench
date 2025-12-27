import { Handle, Position, type NodeProps } from 'reactflow';
import { useEffect, useRef } from 'react';
import { useStore } from '@/state/store';
import { useShallow } from 'zustand/react/shallow';
import { selectNodeMessages } from '@/state/selectors';
import type { AgentNodeData } from '@/types/graph';
import { MessageBubble } from './MessageBubble';
import { cn } from '@/utils/cn';

export function AgentNodeCard({ id, data }: NodeProps<AgentNodeData>) {
    // Select messages for this node with useShallow
    const messages = useStore(
        useShallow((state) => selectNodeMessages(state, id))
    );
    const messagesContainerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const container = messagesContainerRef.current;
        if (!container) {
            return;
        }
        container.scrollTop = container.scrollHeight;
    }, [messages.length]);

    return (
        <div className="bg-card text-card-foreground border rounded-lg shadow-md w-[400px] h-[350px] flex flex-col overflow-hidden ring-1 ring-border">
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-muted-foreground !border-2 !border-background" />

            <div className={cn(
                "p-2 px-3 border-b flex justify-between items-center",
                data.status === 'running' ? 'bg-primary/5' : 'bg-muted/10'
            )}>
                <div className="flex items-center gap-2">
                    <div className={cn(
                        "w-2 h-2 rounded-full",
                        data.status === 'running' ? "bg-blue-500 animate-pulse" :
                            data.status === 'done' ? "bg-green-500" : "bg-gray-300"
                    )} />
                    <span className="font-semibold text-sm">{data.title || data.kind}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase text-muted-foreground font-mono">
                        {data.kind}
                    </span>
                    <button
                        className="p-1 hover:bg-background rounded-md text-muted-foreground hover:text-primary transition-colors"
                        onClick={(e) => {
                            e.stopPropagation();
                            useStore.getState().setActiveNode(id);
                            useStore.getState().setUiMode('focus');
                        }}
                        title="Focus on this agent"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                        </svg>
                    </button>
                </div>
            </div>

            <div
                ref={messagesContainerRef}
                className="flex-1 p-3 overflow-y-auto bg-background/50 space-y-2 nodrag"
            >
                {messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-xs text-muted-foreground italic">
                        Waiting for activity...
                    </div>
                ) : (
                    messages.map((msg) => (
                        <MessageBubble key={msg.id} message={msg} />
                    ))
                )}
            </div>

            <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-muted-foreground !border-2 !border-background" />
        </div>
    );
}
