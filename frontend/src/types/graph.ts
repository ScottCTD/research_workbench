import type { Node, Edge } from 'reactflow';

export type AgentKind = 'general_assistant' | 'planner' | 'researcher' | 'report_writer';

export type AgentNodeData = {
    kind: AgentKind;
    status: 'idle' | 'running' | 'done' | 'failed';
    title?: string;
    // Normalized state: messages are stored separately by nodeId
};

export type ResearchNode = Node<AgentNodeData>;
export type ResearchEdge = Edge;

export type MessageKind = 'human' | 'assistant' | 'tool';

export type ToolStatus = 'running' | 'success' | 'failure';

// Content structure
export type ToolCallPayload = {
    toolName: string;
    input: any;
    output?: any; // streaming updates go here
    status: ToolStatus;
    timestamp: number;
};

export type Message = {
    id: string;
    nodeId: string; // The node this message belongs to
    kind: MessageKind;
    content: string; // Markdown text for chat, or summary for tool
    toolCall?: ToolCallPayload; // Only if kind === 'tool'
    timestamp: number;
};
