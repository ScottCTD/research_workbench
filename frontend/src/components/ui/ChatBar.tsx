import { useState } from 'react';
import { useStore } from '@/state/store';
import { selectCanUserInput } from '@/state/selectors';

export function ChatBar() {
    const canInput = useStore(selectCanUserInput);
    const [input, setInput] = useState('');

    // In a real app, we'd dispatch to backend
    const sendMessage = useStore((state) => state.sendMessage);

    if (!canInput) return null;

    const handleSend = () => {
        if (!input.trim()) return;
        sendMessage(input);
        setInput('');
    };

    return (
        <div className="flex gap-2 p-2 bg-background border-t">
            <input
                className="flex-1 bg-muted/20 border-input border p-2 rounded focus:outline-none focus:ring-1 focus:ring-primary"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
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
        </div>
    );
}
