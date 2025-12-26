import React from 'react';
import { Handle, Position } from 'reactflow';
import { cn } from '@/lib/utils';
import { User, Bot } from 'lucide-react';

export type MessageNodeData = {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: number;
};

export function MessageNode({ data }: { data: MessageNodeData }) {
    const isUser = data.role === 'user';

    return (
        <div className={cn(
            "min-w-[200px] max-w-[400px] rounded-lg border shadow-sm p-4 bg-white",
            isUser ? "border-blue-200 bg-blue-50/30" : "border-gray-200"
        )}>
            <div className="flex items-start gap-3">
                <div className={cn(
                    "p-2 rounded-full shrink-0 flex items-center justify-center w-8 h-8",
                    isUser ? "bg-blue-100 text-blue-600" : "bg-purple-100 text-purple-600"
                )}>
                    {isUser ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="flex flex-col gap-1 overflow-hidden">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        {isUser ? 'User' : 'Assistant'}
                    </span>
                    <div className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed font-sans">
                        {data.content || <span className="text-gray-400 italic">Thinking...</span>}
                    </div>
                </div>
            </div>

            {/* Input Handle (Target) - Top */}
            <Handle
                type="target"
                position={Position.Top}
                className={cn("!w-2 !h-2", isUser ? "!bg-blue-300" : "!bg-gray-300")}
            />

            {/* Output Handle (Source) - Bottom */}
            <Handle
                type="source"
                position={Position.Bottom}
                className={cn("!w-2 !h-2", isUser ? "!bg-blue-300" : "!bg-gray-300")}
            />
        </div>
    );
}
