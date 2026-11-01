export interface ServerEvent {
  event: string;
  data: any;
}

/** Parse one SSE block ("event: x\ndata: {...}"). Returns null for comments / malformed JSON. */
export function parseBlock(block: string): ServerEvent | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join('\n')) };
  } catch {
    return null;
  }
}

/** fetch() + ReadableStream based SSE reader (EventSource can't POST). Handles chunk boundaries. */
export async function* parseSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<ServerEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      let i: number;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const ev = parseBlock(buf.slice(0, i));
        buf = buf.slice(i + 2);
        if (ev) yield ev;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
