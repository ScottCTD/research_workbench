import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { cn } from '@/lib/utils';
import { Terminal, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight, Play } from 'lucide-react';

export type ToolNodeData = {
    toolName: string;
    input: string; // JSON string
    output?: string; // JSON string
    status: 'running' | 'success' | 'error';
    timestamp?: number;
};

export function ToolNode({ data }: { data: ToolNodeData }) {
    const [expanded, setExpanded] = useState(false);
    const isRunning = data.status === 'running';
    const isError = data.status === 'error';

    return (
        <div className={cn(
            "w-[350px] rounded-lg border bg-white shadow-sm transition-all duration-200",
            isRunning ? "border-amber-300 ring-4 ring-amber-50" :
                isError ? "border-red-200" : "border-gray-200"
        )}>
            {/* Header */}
            <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50/50 rounded-t-lg transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "p-1.5 rounded-md",
                        isRunning ? "bg-amber-100 text-amber-600" :
                            isError ? "bg-red-100 text-red-600" : "bg-gray-100 text-gray-600"
                    )}>
                        <Terminal size={14} />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xs font-semibold text-gray-700 font-mono">
                            {data.toolName}
                        </span>
                        <span className="text-[10px] text-gray-400 capitalize">
                            {data.status}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {isRunning && <Loader2 size={14} className="animate-spin text-amber-500" />}
                    {!isRunning && !isError && <CheckCircle2 size={14} className="text-green-500" />}
                    {isError && <XCircle size={14} className="text-red-500" />}
                    {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
                </div>
            </div>

            {/* Body (Expanded) */}
            {expanded && (
                <div className="border-t border-gray-100 p-3 bg-gray-50/30 rounded-b-lg space-y-3">
                    {/* Input */}
                    <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                            <Play size={10} /> Input
                        </div>
                        <div className="bg-white border border-gray-200 rounded p-2 overflow-x-auto text-xs font-mono text-gray-600 shadow-sm max-h-[150px] custom-scrollbar">
                            {data.input}
                        </div>
                    </div>

                    {/* Output (if available) */}
                    {data.output && (
                        <div className="space-y-1">
                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                                <CheckCircle2 size={10} /> Output
                            </div>
                            <div className="bg-white border border-gray-200 rounded p-2 overflow-x-auto text-xs font-mono text-gray-600 shadow-sm max-h-[200px] custom-scrollbar">
                                {data.output}
                            </div>
                        </div>
                    )}
                </div>
            )}

            <Handle type="target" position={Position.Top} className="!bg-gray-300 !w-2 !h-2" />
            <Handle type="source" position={Position.Bottom} className="!bg-gray-300 !w-2 !h-2" />
        </div>
    );
}
