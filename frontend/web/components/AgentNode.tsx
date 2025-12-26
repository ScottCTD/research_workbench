import React, { useState } from "react";
import { Handle, Position } from "reactflow";
import { CheckCircle2, Circle, Loader2, ChevronDown, ChevronRight, Terminal, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

export type LogItem = {
    id: string;
    type: "thought" | "tool_call" | "tool_output";
    content: string;
    name?: string;
    timestamp: number;
};

export type AgentNodeData = {
    label: string;
    status: "running" | "done" | "error";
    logs: LogItem[];
};

export function AgentNode({ data }: { data: AgentNodeData }) {
    const [expanded, setExpanded] = useState(true);

    // DEBUG LOG
    console.log(`Render AgentNode [${data.label}]: status=${data.status}, logs=${data.logs.length}`);

    return (
        <div className={cn(
            "w-[400px] rounded-lg border bg-white shadow-sm transition-all duration-300",
            data.status === "running" ? "border-blue-300 ring-2 ring-blue-100" : "border-gray-200 hover:shadow-md"
        )}>
            {/* Header */}
            <div
                className="flex items-center justify-between p-3 border-b border-gray-100 cursor-pointer bg-gray-50/50 rounded-t-lg"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "p-1.5 rounded-md",
                        data.status === "running" ? "bg-blue-50 text-blue-600" : "bg-green-50 text-green-600"
                    )}>
                        <Bot size={18} />
                    </div>
                    <div className="flex flex-col">
                        <h3 className="text-sm font-semibold text-gray-800">{data.label}</h3>
                        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-medium">{data.status}</span>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {data.status === "running" ? (
                        <Loader2 size={16} className="animate-spin text-blue-500" />
                    ) : (
                        <CheckCircle2 size={16} className="text-green-500" />
                    )}
                    {expanded ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
                </div>
            </div>

            {/* Body */}
            {expanded && (
                <div className="p-3 space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar bg-white rounded-b-lg">
                    {data.logs.map((log) => (
                        <LogEntry key={log.id} log={log} />
                    ))}
                    {data.logs.length === 0 && (
                        <div className="text-center py-4 text-xs text-gray-400 italic">
                            Initialized...
                        </div>
                    )}
                </div>
            )}

            <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />
            <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
        </div>
    );
}

function LogEntry({ log }: { log: LogItem }) {
    const [showOutput, setShowOutput] = useState(false);

    if (log.type === "thought") {
        return (
            <div className="flex gap-2 text-xs text-gray-600 font-sans leading-relaxed">
                <span className="text-gray-400 font-mono">›</span>
                <p className="whitespace-pre-wrap">{log.content}</p>
            </div>
        );
    }

    if (log.type === "tool_call") {
        return (
            <div className="bg-gray-50 rounded border border-gray-100 p-2">
                <div className="flex items-center gap-2 text-xs text-gray-700 font-medium mb-1">
                    <Terminal size={12} className="text-gray-500" />
                    <span>Call: {log.name}</span>
                </div>
                <div className="text-xs text-gray-500 font-mono break-all line-clamp-2 pl-5">
                    {log.content}
                </div>
            </div>
        );
    }

    if (log.type === "tool_output") {
        return (
            <div className="pl-4 border-l border-gray-200 ml-1">
                <button
                    onClick={() => setShowOutput(!showOutput)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 transition-colors py-1"
                >
                    {showOutput ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <span className="font-medium">Output</span>
                </button>
                {showOutput && (
                    <div className="mt-1 text-xs text-gray-600 font-mono bg-gray-50 p-2 rounded border border-gray-100 overflow-x-auto whitespace-pre-wrap shadow-inner">
                        {log.content}
                    </div>
                )}
            </div>
        );
    }

    return null;
}
