import type { ServerEvent } from '@/types/events';

type EventHandler = (event: ServerEvent) => void;

export class SseClient {
    private eventSource: EventSource | null = null;
    private url: string;
    private onEvent: EventHandler;

    constructor(url: string, onEvent: EventHandler) {
        this.url = url;
        this.onEvent = onEvent;
    }

    connect() {
        if (this.eventSource) return;

        this.eventSource = new EventSource(this.url);

        this.eventSource.onopen = () => {
            console.log('SSE Connected to', this.url);
        };

        this.eventSource.onmessage = (rawEvent) => {
            try {
                // Determine if it's a "ping" or real data
                // Usually SSE libraries just give data in payload, sse-starlette sends {data: json_string}
                // But native EventSource handles 'data' field automatically.
                // If it is 'ping', data might be empty.
                if (!rawEvent.data) return;

                const parsed = JSON.parse(rawEvent.data) as ServerEvent;
                this.onEvent(parsed);
            } catch (err) {
                console.error('Failed to parse SSE event', err, rawEvent.data);
            }
        };

        this.eventSource.onerror = (err) => {
            console.error('SSE Error', err);
            // Optional: auto-reconnect logic or notify error
            this.disconnect();
        };
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}
