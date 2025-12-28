import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types/graph';
import { cn } from '@/utils/cn';
import { ToolCallBubble } from '@/components/tools/ToolCallBubble';

export function MessageBubble({ message }: { message: Message }) {
    if (message.kind === 'tool') {
        return <ToolCallBubble message={message} />;
    }

    const isAssistant = message.kind === 'assistant';
    const isStreaming = Boolean(message.streaming);

    return (
        <div
            className={cn(
                "flex w-full mb-3",
                isAssistant ? "justify-start" : "justify-end"
            )}
        >
            <div
                className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed shadow-sm",
                    isAssistant
                        ? "bg-muted text-foreground"
                        : "bg-primary text-primary-foreground"
                )}
            >
                {isStreaming ? (
                    <div className="whitespace-pre-wrap">
                        {message.content || ""}
                    </div>
                ) : (
                    <div className="max-w-none [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:list-disc [&>ul]:pl-4 [&>ol]:list-decimal [&>ol]:pl-4">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content || ""}
                        </ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
}
