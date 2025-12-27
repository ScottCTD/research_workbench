import { useEffect } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    type NodeTypes
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useStore } from '@/state/store';
import { useShallow } from 'zustand/react/shallow';
import { selectNodes, selectEdges } from '@/state/selectors';
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

    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Apply layout whenever store data changes
    useEffect(() => {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            [...storeNodes],
            [...storeEdges]
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
    }, [storeNodes, storeEdges, setNodes, setEdges]);

    return (
        <div className="w-full h-full">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.1}
            >
                <Background />
                <Controls />
            </ReactFlow>
        </div>
    );
}
