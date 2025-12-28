import type { AgentKind, Message, ToolStatus } from './graph';

export type ServerEvent =
    | { type: 'NODE_CREATED'; payload: { id: string; kind: AgentKind; title?: string } }
    | { type: 'EDGE_CREATED'; payload: { source: string; target: string; id?: string } }
    | { type: 'MESSAGE_APPENDED'; payload: Message }
    | { type: 'MESSAGE_UPDATED'; payload: { id: string; content?: string; append?: boolean; streaming?: boolean } }
    | { type: 'TOOL_UPDATED'; payload: { messageId: string; status?: ToolStatus; output?: any } }
    | { type: 'TOOL_STATUS_CHANGED'; payload: { messageId: string; status: ToolStatus } }
    | { type: 'ACTIVE_NODE_SET'; payload: { id: string } }
    | { type: 'GRAPH_RESET'; payload: {} }
    | { type: 'UI_MODE_SET'; payload: { mode: 'focus' | 'research' } }
    | { type: 'WORKFLOW_STARTED'; payload: { mode?: 'focus' | 'research' } }
    | { type: 'WORKFLOW_COMPLETED'; payload: { reportMessageId?: string } }
    | { type: 'ERROR'; payload: { message: string } };
