import type { ResearchNode, ResearchEdge, Message } from '@/types/graph';
import type { ServerEvent } from '@/types/events';

export type AppState = {
    nodes: Record<string, ResearchNode>;
    edges: Record<string, ResearchEdge>;
    messages: Record<string, Message>;
    nodeMessageIds: Record<string, string[]>;
    activeNodeId: string | null;
    selectedNodeId: string | null;
    uiMode: 'focus' | 'research';
};

export const initialState: AppState = {
    nodes: {},
    edges: {},
    messages: {},
    nodeMessageIds: {},
    activeNodeId: null,
    selectedNodeId: null,
    uiMode: 'focus',
};

export function applyEvent(state: AppState, event: ServerEvent): Partial<AppState> {
    switch (event.type) {
        case 'GRAPH_RESET':
            return initialState;

        case 'NODE_CREATED': {
            const { id, kind, title } = event.payload;
            return {
                nodes: {
                    ...state.nodes,
                    [id]: {
                        id,
                        position: { x: 0, y: 0 }, // Layout will derive real position
                        data: { kind, status: 'idle', title },
                        type: 'agentNode', // Custom node type name
                    },
                },
                nodeMessageIds: {
                    ...state.nodeMessageIds,
                    [id]: [],
                },
                // If it's the first node, make it active
                activeNodeId: state.activeNodeId || id,
            };
        }

        case 'EDGE_CREATED': {
            const { source, target, id } = event.payload;
            const edgeId = id || `${source}->${target}`;
            return {
                edges: {
                    ...state.edges,
                    [edgeId]: {
                        id: edgeId,
                        source,
                        target,
                        animated: true,
                        type: 'smoothstep', // or default
                    },
                },
            };
        }

        case 'MESSAGE_APPENDED': {
            const msg = event.payload;
            return {
                messages: {
                    ...state.messages,
                    [msg.id]: msg,
                },
                nodeMessageIds: {
                    ...state.nodeMessageIds,
                    [msg.nodeId]: [...(state.nodeMessageIds[msg.nodeId] || []), msg.id],
                },
            };
        }

        case 'TOOL_UPDATED': {
            const { messageId, status, output } = event.payload;
            const existingMsg = state.messages[messageId];
            if (!existingMsg || existingMsg.kind !== 'tool' || !existingMsg.toolCall) return {};

            return {
                messages: {
                    ...state.messages,
                    [messageId]: {
                        ...existingMsg,
                        toolCall: {
                            ...existingMsg.toolCall,
                            ...(status ? { status } : {}),
                            ...(output ? { output } : {}),
                        },
                    },
                },
            };
        }

        // We also need to handle TOOL_STATUS_CHANGED if using that event
        case 'TOOL_STATUS_CHANGED': {
            const { messageId, status } = event.payload;
            const existingMsg = state.messages[messageId];
            if (!existingMsg || existingMsg.kind !== 'tool' || !existingMsg.toolCall) return {};

            return {
                messages: {
                    ...state.messages,
                    [messageId]: {
                        ...existingMsg,
                        toolCall: {
                            ...existingMsg.toolCall,
                            status
                        }
                    }
                }
            }
        }

        case 'ACTIVE_NODE_SET': {
            return { activeNodeId: event.payload.id };
        }

        case 'UI_MODE_SET': {
            return { uiMode: event.payload.mode };
        }

        case 'WORKFLOW_STARTED': {
            return { uiMode: event.payload.mode || 'research' };
        }

        case 'WORKFLOW_COMPLETED': {
            return {};
        }

        default:
            return {};
    }
}
