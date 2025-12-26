"use client";

import React, { useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    Background,
    Controls,
    Panel,
    ReactFlowProvider,
    useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { AgentNode, AgentNodeData, LogItem } from './AgentNode';
import { streamResearch } from '@/lib/api';
import { Play, RotateCcw } from 'lucide-react';

const nodeTypes = {
    agent: AgentNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 400;
const nodeHeight = 200; // estimated

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
    dagreGraph.setGraph({ rankdir: 'TB' });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    nodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        node.targetPosition = 'top' as any;
        node.sourcePosition = 'bottom' as any;

        // We make sure the previous nodes don't jump around too much, 
        // but here we just re-layout everything for simplicity.
        node.position = {
            x: nodeWithPosition.x - nodeWidth / 2,
            y: nodeWithPosition.y - nodeHeight / 2,
        };

        return node;
    });

    return { nodes, edges };
};


export function ResearchCanvas({ runId, messages }: { runId: string | null, messages: { role: string, content: string }[] }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // We use a ref to access current nodes inside processEvent without adding it to dependencies
    const nodesRef = useRef(nodes);
    useEffect(() => {
        nodesRef.current = nodes;
    }, [nodes]);

    // Track mapping from run_id to node_id for visual mapping
    const runIdToNodeId = useRef<Map<string, string>>(new Map());

    // Track active node IDs by name (synchronous lookup to avoid React state race conditions)
    const activeNodesRef = useRef<Map<string, string>>(new Map());

    // Keep track of the last node to connect edges
    const lastNodeId = useRef<string | null>(null);

    // Keep track of processed messages to avoid re-streaming
    const processedMessages = useRef<number>(0);

    const processEvent = useCallback((event: any) => {
        const { event: eventType, run_id, name, data, metadata } = event;
        // console.log("Processing:", eventType, metadata?.langgraph_node); 

        // 1. Handle New Node Creation (Graph Nodes)
        if (eventType === "on_chain_start" && metadata && metadata.langgraph_node) {
            const nodeId = run_id;
            const nodeName = metadata.langgraph_node;

            // Check existence using ref or map
            const exists = runIdToNodeId.current.has(nodeId);

            if (!exists) {
                console.log("Creating Node:", nodeName, nodeId); // DEBUG
                const newNode: Node<AgentNodeData> = {
                    id: nodeId,
                    type: 'agent',
                    data: {
                        label: nodeName,
                        status: 'running',
                        logs: [],
                    },
                    position: { x: 0, y: 0 },
                };

                setNodes((nds) => [...nds, newNode]);

                // Add edge from last node
                if (lastNodeId.current) {
                    const sourceId = lastNodeId.current;
                    setEdges((eds) => addEdge({
                        id: `${sourceId}-${nodeId}`,
                        source: sourceId,
                        target: nodeId,
                        animated: true,
                        style: { stroke: '#94a3b8' }
                    }, eds));
                }

                lastNodeId.current = nodeId;
                runIdToNodeId.current.set(run_id, nodeId);
                activeNodesRef.current.set(nodeName, nodeId);
            }
        }

        // 2. Handle Node Completion
        if (eventType === "on_chain_end" && metadata && metadata.langgraph_node) {
            setNodes((nds) => nds.map(n => {
                if (n.id === run_id) {
                    return {
                        ...n,
                        data: { ...n.data, status: 'done' }
                    };
                }
                return n;
            }));
        }

        // 3. Handle Log Items
        let targetNodeId: string | undefined;

        if (metadata?.langgraph_node) {
            if (runIdToNodeId.current.has(run_id)) {
                targetNodeId = runIdToNodeId.current.get(run_id);
            }
        }

        if (!targetNodeId && metadata?.langgraph_node) {
            // Try synchronous lookup first (solves the race condition)
            if (activeNodesRef.current.has(metadata.langgraph_node)) {
                targetNodeId = activeNodesRef.current.get(metadata.langgraph_node);
            } else {
                // Fallback to searching current nodes state (unlikely to be needed if ref works)
                const matchingNode = nodesRef.current.find(n => n.data.label === metadata.langgraph_node && n.data.status === 'running');
                if (matchingNode) targetNodeId = matchingNode.id;
                else console.warn("Could not resolve targetNodeId for event:", eventType, metadata?.langgraph_node, "Active nodes:", Array.from(activeNodesRef.current.keys())); // DEBUG
            }
        }

        if (targetNodeId) {
            const logId = run_id + eventType;

            if (eventType === "on_chat_model_stream") {
                const content = data?.chunk?.content || "";
                if (content) {
                    setNodes(nds => nds.map(n => {
                        if (n.id === targetNodeId) {
                            const lastLog = n.data.logs[n.data.logs.length - 1];
                            const isThought = lastLog && lastLog.type === 'thought';
                            // console.log(`Updating Node ${n.id} (stream): append? ${isThought}`); // DEBUG

                            if (isThought) {
                                return {
                                    ...n,
                                    data: {
                                        ...n.data,
                                        logs: [
                                            ...n.data.logs.slice(0, -1),
                                            { ...lastLog, content: lastLog.content + content }
                                        ]
                                    }
                                };
                            } else {
                                return {
                                    ...n,
                                    data: {
                                        ...n.data,
                                        logs: [...n.data.logs, {
                                            id: logId,
                                            type: 'thought',
                                            content: content,
                                            timestamp: Date.now()
                                        }]
                                    }
                                };
                            }
                        }
                        return n;
                    }));
                }
            }

            if (eventType === "on_tool_start") {
                setNodes(nds => nds.map(n => {
                    if (n.id === targetNodeId) {
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                logs: [...n.data.logs, {
                                    id: run_id,
                                    type: 'tool_call',
                                    name: name,
                                    content: JSON.stringify(data.input, null, 2),
                                    timestamp: Date.now()
                                }]
                            }
                        };
                    }
                    return n;
                }));
            }

            if (eventType === "on_tool_end") {
                setNodes(nds => nds.map(n => {
                    if (n.id === targetNodeId) {
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                logs: [...n.data.logs, {
                                    id: run_id + "_end",
                                    type: 'tool_output',
                                    name: name,
                                    content: typeof data.output === 'string' ? data.output : JSON.stringify(data.output, null, 2),
                                    timestamp: Date.now()
                                }]
                            }
                        };
                    }
                    return n;
                }));
            }

            // 4. Handle Chat Model End (Fallback/Final answer)
            if (eventType === "on_chat_model_end") {
                const content = data?.output?.content || "";
                if (content) {
                    setNodes(nds => nds.map(n => {
                        if (n.id === targetNodeId) {
                            // Check if we already have a partial thought log for this run (from streaming)
                            // If we do, we might not need to do anything, or we could ensure it's complete.
                            // But since we can't easily link stream chunks to this specific end event without ID matching (which isn't 1:1 on logs),
                            // we'll check if the LAST log is a thought.

                            const lastLog = n.data.logs[n.data.logs.length - 1];

                            // If we already have a thought with content, we assume streaming worked.
                            // But if logs are empty OR last log isn't a thought (e.g. it was a tool output), 
                            // OR the thought content is vastly different (hard to tell), we might append.

                            // Simplest fix: If the last log is NOT a thought, or if it is a thought but empty/short compared to this? 
                            // Actually, if streaming worked, we have the content.

                            // Let's only add if we haven't seen any streaming for this particular interaction?
                            // Difficult to track.

                            // Better heuristic: match by run_id if possible? 
                            // The on_chat_model_end run_id is the same as on_chat_model_stream.
                            // But our logs don't store run_id of the stream event, they generate a custom ID.

                            // Let's just append if it's NOT a tool call.
                            // If the last log is a thought, we assume it's the same one and we update it to be sure (or ignore).
                            // A safer approach for "missing message":
                            // If we have content and the last log is NOT a thought, add it.

                            if (!lastLog || lastLog.type !== 'thought') {
                                return {
                                    ...n,
                                    data: {
                                        ...n.data,
                                        logs: [...n.data.logs, {
                                            id: logId,
                                            type: 'thought',
                                            content: content,
                                            timestamp: Date.now()
                                        }]
                                    }
                                };
                            } else {
                                // If last was thought, maybe update it?
                                // If streaming was partial, this overwrites with full.
                                return {
                                    ...n,
                                    data: {
                                        ...n.data,
                                        logs: [
                                            ...n.data.logs.slice(0, -1),
                                            { ...lastLog, content: content }
                                        ]
                                    }
                                }
                            }
                        }
                        return n;
                    }));
                }
            }
        }

    }, [setNodes, setEdges]);

    // Layout Effect - Only when count changes
    useEffect(() => {
        if (nodes.length > 0) {
            // We keep layout logic minimal to avoid loops
        }
    }, [nodes.length, edges.length]);

    // Reset on Run Change
    useEffect(() => {
        if (runId) {
            setNodes([]);
            setEdges([]);
            lastNodeId.current = null;
            runIdToNodeId.current.clear();
            nodesRef.current = [];
            processedMessages.current = 0;
        }
    }, [runId, setNodes, setEdges]);

    // Handle Streaming for New Messages
    useEffect(() => {
        if (!runId || messages.length === 0) return;

        const newMessagesCount = messages.length;
        if (newMessagesCount <= processedMessages.current) return;

        // Get the latest message (assuming always user)
        const lastMsg = messages[messages.length - 1];
        if (lastMsg.role !== 'user') {
            processedMessages.current = newMessagesCount;
            return;
        }

        // Only process the new ones
        processedMessages.current = newMessagesCount;

        const cleanup = streamResearch(
            runId,
            lastMsg.content,
            processEvent,
            (err) => console.error("Stream error", err),
            () => console.log("Stream complete")
        );

        return () => {
            cleanup();
        };
    }, [runId, messages, processEvent]);

    return (
        <div className="w-full h-full bg-[#FAFBFC]">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.5}
            >
                <Background color="#E2E8F0" gap={20} size={1} />
                <Controls className="bg-white border border-gray-200 text-gray-600 shadow-sm" />
            </ReactFlow>
        </div>
    );
}
