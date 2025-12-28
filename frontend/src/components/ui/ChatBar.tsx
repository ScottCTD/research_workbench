import { useRef, useState } from 'react';
import { useStore } from '@/state/store';
import { selectCanUserInput } from '@/state/selectors';

export function ChatBar() {
    const canInput = useStore(selectCanUserInput);
    const [input, setInput] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);
    const maxLines = 5;

    // In a real app, we'd dispatch to backend
    const sendMessage = useStore((state) => state.sendMessage);
    const clearConversation = useStore((state) => state.clearConversation);

    if (!canInput) return null;

    const handleSend = () => {
        if (!input.trim()) return;
        sendMessage(input);
        setInput('');
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.overflowY = 'hidden';
        }
    };

    return (
        <div className="flex gap-2 p-2 bg-background border-t">
            <textarea
                ref={textareaRef}
                className="flex-1 bg-muted/20 border-input border p-2 rounded focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                value={input}
                onChange={(e) => {
                    const value = e.target.value;
                    setInput(value);
                    const textarea = textareaRef.current;
                    if (!textarea) return;
                    textarea.style.height = 'auto';
                    const lineHeight = Number.parseFloat(getComputedStyle(textarea).lineHeight) || 20;
                    const maxHeight = lineHeight * maxLines;
                    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
                    textarea.style.height = `${nextHeight}px`;
                    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
                }}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                    }
                }}
                placeholder="Type a message..."
                autoFocus
            />
            <button
                onClick={handleSend}
                disabled={!input.trim()}
                className="bg-primary text-primary-foreground px-4 py-2 rounded font-medium disabled:opacity-50"
            >
                Send
            </button>
            <button
                onClick={() => {
                    clearConversation();
                    setInput('');
                    if (textareaRef.current) {
                        textareaRef.current.style.height = 'auto';
                        textareaRef.current.style.overflowY = 'hidden';
                    }
                }}
                className="bg-muted text-foreground px-4 py-2 rounded font-medium hover:bg-muted/80"
            >
                Clear
            </button>
        </div>
    );
}
