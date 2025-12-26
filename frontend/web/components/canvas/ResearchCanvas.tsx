"use client";

import React, { useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    Node,
    Edge,
    Background,
    Controls,
    Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { streamResearch } from '@/lib/api';
import { MessageNode } from './nodes/MessageNode';
import { ToolNode } from './nodes/ToolNode';

const nodeTypes = {
    message: MessageNode,
    tool: ToolNode,
};

// Layout options
const NODE_WIDTH = 350;
const NODE_HEIGHT = 150;
const GROUP_PADDING = 30;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
    if (nodes.length === 0) return { nodes, edges };

    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setDefaultNodeLabel(() => ({ width: NODE_WIDTH, height: NODE_HEIGHT }));
    dagreGraph.setGraph({ rankdir: 'TB', align: 'UL', nodesep: 50, ranksep: 50, marginx: 20, marginy: 20 });

    const layoutNodes = nodes.filter((node) => node && node.id !== undefined && node.id !== null);
    const groupNodes = layoutNodes.filter((node) => node.type === 'group');
    const leafNodes = layoutNodes.filter((node) => node.type !== 'group');
    const leafNodeIds = new Set(leafNodes.map((node) => node.id));

    leafNodes.forEach((node) => {
        const width = node.width || NODE_WIDTH;
        const height = node.height || NODE_HEIGHT;
        dagreGraph.setNode(node.id, { width, height });
    });

    const layoutEdges = edges.filter(
        (edge) => edge
            && leafNodeIds.has(edge.source)
            && leafNodeIds.has(edge.target)
    );
    layoutEdges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    try {
        dagre.layout(dagreGraph);
    } catch (err) {
        console.error("Dagre layout failed, falling back to current positions.", err);
        return { nodes, edges };
    }

    // Store absolute positions first
    const absolutePositions = new Map();
    leafNodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        if (!nodeWithPosition) {
            return;
        }
        // Dagre gives center usually
        // But for clusters? "Information about the bounding box of the cluster is contained in the node."
        // x, y, width, height. x/y is center.

        // Defaults
        const width = nodeWithPosition.width || node.width || NODE_WIDTH;
        const height = nodeWithPosition.height || node.height || NODE_HEIGHT;

        absolutePositions.set(node.id, {
            x: nodeWithPosition.x - width / 2,
            y: nodeWithPosition.y - height / 2,
            width,
            height
        });
    });

    // Compute group bounds based on children positions.
    groupNodes.forEach((groupNode) => {
        const children = layoutNodes.filter((node) => node.parentNode === groupNode.id);
        const childPositions = children.map((child) => absolutePositions.get(child.id)).filter(Boolean) as Array<{ x: number; y: number; width: number; height: number }>;
        if (childPositions.length === 0) {
            const fallbackX = typeof groupNode.position?.x === 'number' ? groupNode.position.x : 0;
            const fallbackY = typeof groupNode.position?.y === 'number' ? groupNode.position.y : 0;
            absolutePositions.set(groupNode.id, {
                x: fallbackX,
                y: fallbackY,
                width: groupNode.width || NODE_WIDTH,
                height: groupNode.height || NODE_HEIGHT,
            });
            return;
        }

        const minX = Math.min(...childPositions.map((pos) => pos.x));
        const minY = Math.min(...childPositions.map((pos) => pos.y));
        const maxX = Math.max(...childPositions.map((pos) => pos.x + pos.width));
        const maxY = Math.max(...childPositions.map((pos) => pos.y + pos.height));

        absolutePositions.set(groupNode.id, {
            x: minX - GROUP_PADDING,
            y: minY - GROUP_PADDING,
            width: (maxX - minX) + GROUP_PADDING * 2,
            height: (maxY - minY) + GROUP_PADDING * 2,
        });
    });

    const layoutedNodes = nodes.map((node) => {
        const absPos = absolutePositions.get(node.id);
        if (!absPos) {
            return node;
        }

        let position = { x: absPos.x, y: absPos.y };

        // Convert to relative if has parent
        if (node.parentNode) {
            const parentPos = absolutePositions.get(node.parentNode);
            if (parentPos) {
                position = {
                    x: absPos.x - parentPos.x,
                    y: absPos.y - parentPos.y
                };
            }
        }

        // If it's a group, specific handling
        if (node.type === 'group') {
            return {
                ...node,
                position,
                style: {
                    ...node.style,
                    width: absPos.width,
                    height: absPos.height,
                }
            }
        }

        return {
            ...node,
            position,
        };
    });

    return { nodes: layoutedNodes, edges };
};


export function ResearchCanvas({ runId, messages }: { runId: string | null, messages: { role: string, content: string }[] }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // To handle streaming updates efficiently
    const nodesRef = useRef(nodes);
    const edgesRef = useRef(edges);

    useEffect(() => {
        nodesRef.current = nodes;
        edgesRef.current = edges;
    }, [nodes, edges]);

    // Graph Building State
    const processedMessages = useRef<number>(0);
    const runIdToNodeId = useRef<Map<string, string>>(new Map()); // maps run_id (or event id) to node id
    const activeAgentStack = useRef<string[]>([]); // stack of agent node IDs
    const lastNodeInChain = useRef<string | null>(null); // To connect the next node to

    // Initial Layout Effect (optional, or call it on every major change)
    // We might want to debounce layout updates

    const processEvent = useCallback((event: any) => {
        const { event: eventType, run_id, name, data, metadata } = event;
        // console.log("Event:", eventType, name, run_id);

        let currentNodes = [...nodesRef.current];
        let currentEdges = [...edgesRef.current];
        let changed = false;

        const parentId = activeAgentStack.current.length > 0 ? activeAgentStack.current[activeAgentStack.current.length - 1] : undefined;

        // Helper to add node
        const createNode = (id: string, type: string, nodeData: any, parent?: string) => {
            const newNode: Node = {
                id,
                type,
                data: nodeData,
                position: { x: 0, y: 0 }, // Layout will fix this
                parentNode: parent,
                extent: parent ? 'parent' : undefined,
            };

            // Add to nodes
            currentNodes.push(newNode);

            // IMMEDIATE SYNC REF
            nodesRef.current = currentNodes;

            // Connect to last node in the chain
            if (lastNodeInChain.current) {
                // Check to avoid self-loops or duplicate edges
                const edgeId = `${lastNodeInChain.current}-${id}`;
                if (!currentEdges.find(e => e.id === edgeId)) {
                    currentEdges.push({
                        id: edgeId,
                        source: lastNodeInChain.current,
                        target: id,
                        animated: true,
                        style: { stroke: '#cbd5e1' }
                    });
                    // IMMEDIATE SYNC REF
                    edgesRef.current = currentEdges;
                }
            }

            lastNodeInChain.current = id;
            changed = true;
            return newNode;
        }

        // 0. Subgraph / Agent Start
        // We look for specific LangGraph nodes to group execution
        if (eventType === "on_chain_start" && metadata?.langgraph_node) {
            const nodeName = metadata.langgraph_node;
            const nodeId = run_id;

            // Only visualize specific "agent" nodes as Groups to avoid clutter
            // e.g. 'general_assistant', 'planner', 'write_report'
            // We skip '_entry_', '_end_', etc.
            const importantNodes = ['general_assistant', 'planner', 'write_report'];

            if (importantNodes.includes(nodeName) && !currentNodes.find(n => n.id === nodeId)) {

                const groupNode: Node = {
                    id: nodeId,
                    type: 'group',
                    data: { label: nodeName },
                    position: { x: 0, y: 0 },
                    style: {
                        backgroundColor: 'rgba(240, 244, 255, 0.5)',
                        border: '1px dashed #94a3b8',
                        borderRadius: '8px',
                        padding: '10px'
                    },
                    parentNode: parentId
                };

                currentNodes.push(groupNode);

                // Set stack to enter this group
                activeAgentStack.current.push(nodeId);

                changed = true;
            }
        }

        // 1. Agent End
        if (eventType === "on_chain_end" && metadata?.langgraph_node) {
            const nodeName = metadata.langgraph_node;
            // Pop from stack if it matches top
            if (activeAgentStack.current.length > 0 && activeAgentStack.current[activeAgentStack.current.length - 1] === run_id) {
                activeAgentStack.current.pop();
            }
        }

        // 2. Chat Model Stream (Thinking / AI Message)
        if (eventType === "on_chat_model_stream") {
            const modelRunId = run_id;
            const content = data?.chunk?.content || "";

            // If empty content, skip
            if (!content) return;

            const existingNodeIndex = currentNodes.findIndex(n => n.id === modelRunId);

            if (existingNodeIndex !== -1) {
                // Update existing
                const existingNode = currentNodes[existingNodeIndex];
                const newData = {
                    ...existingNode.data,
                    content: existingNode.data.content + content
                };
                currentNodes[existingNodeIndex] = { ...existingNode, data: newData };
                changed = true;
            } else {
                // Create New Message Node
                // Only create if content is not empty

                // Try to determine parent:
                // If we are inside an agent stack, use that.
                // If not, maybe we missed the start event?

                // Fallback: Check if we are inside a context via metadata?
                // metadata: { langgraph_node: 'general_assistant', ... }
                // Warning: on_chat_model_stream might NOT have langgraph_node in metadata sometimes, 
                // but usually it inherits tags/metadata.

                let effectiveParentId = parentId;

                createNode(modelRunId, 'message', {
                    role: 'assistant',
                    content: content
                }, effectiveParentId);

                runIdToNodeId.current.set(modelRunId, modelRunId);
            }
        }

        // 3. Tool Start
        if (eventType === "on_tool_start") {
            const toolRunId = run_id;
            createNode(toolRunId, 'tool', {
                toolName: name,
                input: JSON.stringify(data.input, null, 2),
                status: 'running'
            }, parentId);

            runIdToNodeId.current.set(toolRunId, toolRunId);
        }

        // 4. Tool End
        if (eventType === "on_tool_end") {
            const toolRunId = run_id;
            const existingNodeIndex = currentNodes.findIndex(n => n.id === toolRunId);

            if (existingNodeIndex !== -1) {
                const existingNode = currentNodes[existingNodeIndex];
                const newData = {
                    ...existingNode.data,
                    output: typeof data.output === 'string' ? data.output : JSON.stringify(data.output, null, 2),
                    status: 'success'
                };
                currentNodes[existingNodeIndex] = { ...existingNode, data: newData };
                changed = true;
            }
        }

        if (changed) {
            // Ensure refs are updated for any modifications (updates, not just creation)
            nodesRef.current = currentNodes;
            edgesRef.current = currentEdges;

            setNodes(currentNodes);
            setEdges(currentEdges);
        }

    }, []); // Refs handle dependencies

    // Layout Effect
    const lastLayoutCounts = useRef({ nodes: 0, edges: 0 });
    useEffect(() => {
        if (nodes.length === 0) return;

        // Check if structure changed (counts mismatch)
        if (nodes.length !== lastLayoutCounts.current.nodes || edges.length !== lastLayoutCounts.current.edges) {
            lastLayoutCounts.current = { nodes: nodes.length, edges: edges.length };

            // Apply Dagre Layout
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges);

            // We use setNodes to update positions.
            // Note: This might conflict with streaming updates if we are not careful, 
            // but since streaming updates data and this updates position, usually fine if we merge?
            // React Flow nodes state is atomic. 
            // If processEvent runs, it updates 'data'. If this runs, it updates 'position'.
            // Race condition: 
            // 1. processEvent gets 'nodes' (old pos, new data) -> sets 'nodes'
            // 2. layout gets 'nodes' (old/new data, new pos) -> sets 'nodes'
            // Result: One might overwrite the other.

            // Ideally layout should be calculated inside processEvent when adding nodes?
            // But processEvent is frequent. 
            // Let's run layout ONLY when adding nodes in processEvent?

            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        }
    }, [nodes.length, edges.length, setNodes, setEdges]);

    // Handle initial user message (Manual)
    useEffect(() => {
        // Only show a static user message when no run is active.
        if (!runId && messages.length > 0 && nodes.length === 0) {
            const firstMsg = messages[0];
            if (firstMsg.role === 'user') {
                const id = 'user-root';
                const userNode: Node = {
                    id,
                    type: 'message',
                    data: { role: 'user', content: firstMsg.content },
                    position: { x: 0, y: 0 }
                };
                setNodes([userNode]);
                lastNodeInChain.current = id;
            }
        }
    }, [messages, runId, nodes.length, setNodes]);


    // Streaming logic reused
    // Reset on Run Change
    useEffect(() => {
        if (runId) {
            // Check if we are retrying or new run.
            // If completely new run, clear.
            // For now we assume new run = clear.
            if (runIdToNodeId.current.has(runId)) return; // Already tracking?

            // Wait, if it's the SAME runId, we shouldn't clear. 
            // Logic:
            // setNodes([]); 
            // lastNodeInChain.current = null;
            // activeAgentStack.current = [];
            // runIdToNodeId.current.clear();
        }
    }, [runId]);

    // Handle Streaming
    useEffect(() => {
        if (!runId || messages.length === 0) return;

        // This is complex because messages keeps growing.
        // We only want to stream normally.

        // Reuse the logic from original but simpler:
        // We trigger streamResearch ONLY for the latest user message.

        const newMessagesCount = messages.length;
        if (newMessagesCount <= processedMessages.current) return;

        const lastMsg = messages[messages.length - 1];
        // Only stream if the last message is from user (initiating action)

        if (lastMsg.role === 'user') {
            // Add User Node first if not exists
            // (Logic above might have added it, or we add here)

            processedMessages.current = newMessagesCount;

            // If we already have a user-root, we append?
            // Graph can have multiple user nodes? Yes.

            // Let's rely on streamResearch events mostly.
            // But streamResearch events don't include the User's input usually, they start with agent execution.

            // So we must manually add the User Node for this turn.
            const userNodeId = `user-${Date.now()}`;
            setNodes((nds) => {
                const newNode: Node = {
                    id: userNodeId,
                    type: 'message',
                    data: { role: 'user', content: lastMsg.content },
                    position: { x: 0, y: 0 },
                };

                // Connect to previous if exists
                const sourceNodeId = lastNodeInChain.current;
                if (sourceNodeId) {
                    setEdges((eds) => [...eds, {
                        id: `${sourceNodeId}-${userNodeId}`,
                        source: sourceNodeId,
                        target: userNodeId,
                        animated: true
                    }]);
                }

                lastNodeInChain.current = userNodeId;
                return [...nds, newNode];
            });

            streamResearch(
                runId,
                lastMsg.content,
                processEvent,
                (err) => console.error("Stream error", err),
                () => console.log("Stream complete")
            );
        }

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
                minZoom={0.1}
                proOptions={{ hideAttribution: true }}
            >
                <Background color="#E2E8F0" gap={20} size={1} />
                <Controls className="bg-white border border-gray-200 text-gray-600 shadow-sm" />
                <Panel position="top-right" className='bg-white/80 backdrop-blur p-2 rounded shadow-sm border border-gray-200 text-xs text-gray-500'>
                    Trace View (Experiment)
                </Panel>
            </ReactFlow>
        </div>
    );
}
