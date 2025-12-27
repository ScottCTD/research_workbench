import { Modal } from '@/components/ui/Modal';
import type { ToolCallPayload } from '@/types/graph';

interface ToolCallDetailsPanelProps {
    isOpen: boolean;
    onClose: () => void;
    toolCall: ToolCallPayload;
}

export function ToolCallDetailsPanel({ isOpen, onClose, toolCall }: ToolCallDetailsPanelProps) {
    const formatJson = (data: any) => {
        try {
            return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        } catch (e) {
            return String(data);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Tool: ${toolCall.toolName}`}>
            <div className="space-y-4">
                <div>
                    <h4 className="text-sm font-medium mb-1">Status</h4>
                    <span className="text-xs px-2 py-1 rounded bg-muted uppercase font-mono">{toolCall.status}</span>
                </div>

                <div>
                    <h4 className="text-sm font-medium mb-1">Input</h4>
                    <div className="text-xs rounded border bg-muted/30 p-2 overflow-x-auto">
                        <pre className="font-mono whitespace-pre-wrap break-all">
                            {formatJson(toolCall.input)}
                        </pre>
                    </div>
                </div>

                <div>
                    <h4 className="text-sm font-medium mb-1">Output</h4>
                    {toolCall.output ? (
                        <div className="text-xs rounded border bg-muted/30 p-2 overflow-x-auto">
                            <pre className="font-mono whitespace-pre-wrap break-all">
                                {formatJson(toolCall.output)}
                            </pre>
                        </div>
                    ) : (
                        <p className="text-xs text-muted-foreground italic">No output yet...</p>
                    )}
                </div>
            </div>
        </Modal>
    );
}
