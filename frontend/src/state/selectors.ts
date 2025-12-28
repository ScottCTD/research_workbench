import type { AppState } from './reducers';
import type { ResearchNode, ResearchEdge, Message } from '@/types/graph';

export const selectNodes = (state: AppState): ResearchNode[] => Object.values(state.nodes);
export const selectEdges = (state: AppState): ResearchEdge[] => Object.values(state.edges);

export const selectActiveNode = (state: AppState) =>
    state.activeNodeId ? state.nodes[state.activeNodeId] : null;

export const selectSelectedNode = (state: AppState) =>
    state.selectedNodeId ? state.nodes[state.selectedNodeId] : null;

// Get messages for a specific node
export const selectNodeMessages = (state: AppState, nodeId: string): Message[] => {
    const ids = state.nodeMessageIds[nodeId] || [];
    return ids.map((id) => state.messages[id]).filter(Boolean);
};

export const selectAgentMessages = (state: AppState, kind: ResearchNode['data']['kind']): Message[] => {
    const agentNodeIds = new Set(
        Object.values(state.nodes)
            .filter((node) => node.data.kind === kind)
            .map((node) => node.id)
    );

    return Object.values(state.messages).filter((msg) => agentNodeIds.has(msg.nodeId));
};

export const selectCanUserInput = (state: AppState): boolean => {
    const activeNode = selectActiveNode(state);
    if (state.uiMode === 'research') return false;
    if (!activeNode) return true;

    // Check if active node is general_assistant
    if (activeNode.data.kind !== 'general_assistant') return false;

    // Check latest message
    // We need to get the latest message of the active node
    const messages = selectNodeMessages(state, activeNode.id);
    if (messages.length === 0) return true; // Start of chat

    const lastMsg = messages[messages.length - 1];
    // Simple heuristic: if last msg is tool call, user can't input (waiting for tool).
    // If last msg is assistant text, user can input.
    // If last msg is human, assistant is thinking (maybe?)

    if (lastMsg.kind === 'tool') return false;
    if (lastMsg.kind === 'human') return false; // Waiting for response

    return true;
};
