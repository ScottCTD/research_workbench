import { motion } from 'framer-motion';
import { GraphCanvas } from '@/components/canvas/GraphCanvas';
import { useStore } from '@/state/store';

export function ResearchView() {
    return (
        <motion.div
            className="h-full w-full bg-slate-50 relative overflow-hidden"
            initial={{ opacity: 0, scale: 1.05 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
        >
            <div className="absolute top-4 left-4 z-10 bg-background/80 backdrop-blur p-2 rounded border shadow-sm text-sm font-medium">
                Research Map
            </div>

            <div className="absolute top-4 right-4 z-10">
                <button
                    onClick={() => {
                        const state = useStore.getState();
                        // Find the root/initial agent (usually general_assistant or the first one)
                        const rootNode = Object.values(state.nodes).find(n => n.data.kind === 'general_assistant') || Object.values(state.nodes)[0];
                        if (rootNode) {
                            state.setActiveNode(rootNode.id);
                        }
                        state.setUiMode('focus');
                    }}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded shadow hover:bg-primary/90 transition-colors text-sm font-medium"
                >
                    Back to Chat
                </button>
            </div>

            <div className="w-full h-full">
                <GraphCanvas />
            </div>
        </motion.div>
    );
}
