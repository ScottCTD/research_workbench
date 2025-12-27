import type { ServerEvent } from '@/types/events';

export const deepResearchFixture: ServerEvent[] = [
    // 1. Initial GA Node
    { type: 'GRAPH_RESET', payload: {} },
    { type: 'NODE_CREATED', payload: { id: 'ga-1', kind: 'general_assistant', title: 'General Assistant' } },
    { type: 'ACTIVE_NODE_SET', payload: { id: 'ga-1' } },
    { type: 'WORKFLOW_STARTED', payload: { mode: 'focus' } },

    // 2. Chat interaction
    {
        type: 'MESSAGE_APPENDED',
        payload: {
            id: 'msg-1',
            nodeId: 'ga-1',
            kind: 'human',
            content: 'Compare A vs B deeply.',
            timestamp: Date.now(),
        },
    },
    {
        type: 'MESSAGE_APPENDED',
        payload: {
            id: 'msg-2',
            nodeId: 'ga-1',
            kind: 'assistant',
            content: 'I will start a deep research task for this.',
            timestamp: Date.now() + 1000,
        },
    },

    // 3. Tool Call starts deep research
    {
        type: 'MESSAGE_APPENDED',
        payload: {
            id: 'msg-3',
            nodeId: 'ga-1',
            kind: 'tool',
            content: 'Starting deep research...',
            toolCall: {
                toolName: 'deep_research.start',
                input: { query: 'Compare A vs B' },
                status: 'running',
                timestamp: Date.now() + 2000,
            },
            timestamp: Date.now() + 2000,
        },
    },

    // 4. Workflow transition
    { type: 'WORKFLOW_STARTED', payload: { mode: 'research' } },

    // 5. Planner Node
    { type: 'NODE_CREATED', payload: { id: 'planner-1', kind: 'planner', title: 'Research Planner' } },
    { type: 'EDGE_CREATED', payload: { source: 'ga-1', target: 'planner-1' } },
    { type: 'ACTIVE_NODE_SET', payload: { id: 'planner-1' } },
    // Wait, actively executing node is Planner now.

    {
        type: 'MESSAGE_APPENDED',
        payload: {
            id: 'msg-p1',
            nodeId: 'planner-1',
            kind: 'assistant',
            content: 'Analyzing request and generating research plan...',
            timestamp: Date.now() + 3000,
        }
    },

    // 6. Researchers in parallel
    { type: 'NODE_CREATED', payload: { id: 'res-1', kind: 'researcher', title: 'Researcher A' } },
    { type: 'EDGE_CREATED', payload: { source: 'planner-1', target: 'res-1' } },

    { type: 'NODE_CREATED', payload: { id: 'res-2', kind: 'researcher', title: 'Researcher B' } },
    { type: 'EDGE_CREATED', payload: { source: 'planner-1', target: 'res-2' } },

    // Stream updates
    {
        type: 'MESSAGE_APPENDED',
        payload: {
            id: 'msg-r1',
            nodeId: 'res-1',
            kind: 'tool',
            content: 'Searching web...',
            toolCall: {
                toolName: 'web_search',
                input: { query: 'Topic A analysis' },
                status: 'running',
                timestamp: Date.now() + 4000
            },
            timestamp: Date.now() + 4000
        }
    },
    {
        type: 'TOOL_UPDATED',
        payload: {
            messageId: 'msg-r1',
            status: 'success',
            output: { results: ['Result A1', 'Result A2'] }
        }
    },

    // ... Report writer and completion can be simulated later or expanded here
];
