import { useState } from 'react';
import type { Message } from '@/types/graph';
import { cn } from '@/utils/cn';
import { ToolCallDetailsPanel } from './ToolCallDetailsPanel';

export function ToolCallBubble({ message }: { message: Message }) {
    const { toolCall } = message;
    const [isOpen, setIsOpen] = useState(false);

    if (!toolCall) return null;

    return (
        <>
            <div className="w-full mb-3 flex justify-start">
                <div
                    onClick={() => setIsOpen(true)}
                    className="w-[90%] bg-card border rounded-md p-2 text-xs shadow-sm cursor-pointer hover:border-primary transition-colors hover:bg-muted/50"
                >
                    <div className="flex items-center justify-between mb-1 pb-1 border-b border-border/50">
                        <span className="font-mono font-bold text-primary truncate max-w-[150px]">{toolCall.toolName}</span>
                        <span className={cn(
                            "text-[10px] uppercase font-bold px-1.5 py-0.5 rounded",
                            toolCall.status === 'running' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' :
                                toolCall.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                                    'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                        )}>
                            {toolCall.status}
                        </span>
                    </div>
                    <div className="text-muted-foreground font-mono mt-1 opacity-80 truncate">
                        {toolCall.status === 'running' ? 'Executing...' : 'Completed'}
                    </div>
                </div>
            </div>

            <ToolCallDetailsPanel
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                toolCall={toolCall}
            />
        </>
    );
}
