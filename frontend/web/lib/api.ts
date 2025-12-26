export type ResearchEvent = {
    event: string;
    name: string;
    run_id: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tags?: string[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    metadata?: any;
};

const API_BASE = "http://localhost:8000";

export async function startResearch(query: string): Promise<string> {
    const res = await fetch(`${API_BASE}/research/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error("Failed to start research");
    const data = await res.json();
    return data.run_id;
}

export function streamResearch(
    run_id: string,
    query: string,
    onEvent: (event: ResearchEvent) => void,
    onError: (err: unknown) => void,
    onDone: () => void
): () => void {
    const url = `${API_BASE}/research/${run_id}/stream?query=${encodeURIComponent(query)}`;
    // Note: We use fetch and ReadableStream manually if we want POST for init, 
    // but EventSource is GET. Our endpoint is GET.
    const evtSource = new EventSource(url);

    evtSource.onmessage = (e) => {
        if (e.data === "[DONE]") {
            evtSource.close();
            onDone();
            return;
        }
        try {
            const parsed = JSON.parse(e.data);
            if (parsed.type === "error") {
                onError(parsed.message);
            } else {
                onEvent(parsed);
            }
        } catch (err) {
            console.error("Failed to parse event", err);
        }
    };

    evtSource.onerror = (err) => {
        console.error("EventSource failed:", err);
        onError(err);
        evtSource.close();
    };

    return () => {
        evtSource.close();
    };
}
