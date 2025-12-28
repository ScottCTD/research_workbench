import { useEffect, useRef } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    type NodeTypes,
    type ReactFlowInstance
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useStore } from '@/state/store';
import { useShallow } from 'zustand/react/shallow';
import { selectNodes, selectEdges, selectActiveNode } from '@/state/selectors';
import { getLayoutedElements } from './layout';
import { AgentNodeCard } from '@/components/node/AgentNodeCard';

const nodeTypes: NodeTypes = {
    agentNode: AgentNodeCard,
};

export function GraphCanvas() {
    // Use useShallow to ensure stable array references for storeNodes/storeEdges
    // avoiding infinite loops with useSyncExternalStore
    const storeNodes = useStore(useShallow(selectNodes));
    const storeEdges = useStore(useShallow(selectEdges));
    const activeNode = useStore(selectActiveNode);

    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const flowRef = useRef<ReactFlowInstance | null>(null);
    const prevResearcherCountRef = useRef(0);
    const pendingFocusIdRef = useRef<string | null>(null);
    const pendingFocusKindRef = useRef<string | null>(null);

    // Apply layout whenever store data changes
    useEffect(() => {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            [...storeNodes],
            [...storeEdges]
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
    }, [storeNodes, storeEdges, setNodes, setEdges]);

    useEffect(() => {
        if (!activeNode) {
            return;
        }
        pendingFocusIdRef.current = activeNode.id;
        pendingFocusKindRef.current = activeNode.data.kind;
    }, [activeNode?.id, activeNode?.data.kind]);

    useEffect(() => {
        const instance = flowRef.current;
        if (!instance || nodes.length === 0) {
            prevResearcherCountRef.current = 0;
            return;
        }

        const researcherCount = nodes.filter((node) => node.data?.kind === 'researcher').length;
        const pendingId = pendingFocusIdRef.current;
        const pendingKind = pendingFocusKindRef.current;
        const prevResearcherCount = prevResearcherCountRef.current;

        if (pendingId) {
            const targetNode = nodes.find((node) => node.id === pendingId);
            if (targetNode?.position) {
                if (pendingKind === 'researcher' && researcherCount >= 2) {
                    instance.fitView({ padding: 0.35, duration: 500 });
                } else {
                    const width = targetNode.width ?? 400;
                    const height = targetNode.height ?? 350;
                    const centerX = targetNode.position.x + width / 2;
                    const centerY = targetNode.position.y + height / 2;
                    const zoom = pendingKind === 'researcher' ? 0.95 : 1.15;
                    instance.setCenter(centerX, centerY, { zoom, duration: 500 });
                }
                pendingFocusIdRef.current = null;
                pendingFocusKindRef.current = null;
            } else {
                instance.fitView({ padding: 0.2, duration: 500 });
            }
        } else if (researcherCount >= 2 && researcherCount > prevResearcherCount) {
            instance.fitView({ padding: 0.4, duration: 500 });
        }

        prevResearcherCountRef.current = researcherCount;
    }, [nodes, activeNode]);

    return (
        <div className="w-full h-full">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                onInit={(instance) => {
                    flowRef.current = instance;
                }}
                fitView
                minZoom={0.1}
            >
                <Background />
                <Controls />
            </ReactFlow>
        </div>
    );
}
