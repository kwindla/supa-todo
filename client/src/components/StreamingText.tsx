'use client';

import { useCallback, useRef } from 'react';
import { RTVIEvent } from '@pipecat-ai/client-js';
import { useRTVIClientEvent } from '@pipecat-ai/client-react';

interface StreamingTextProps {
  bgColor?: string;
  "clear-pre-text"?: boolean;
  "display-pre-text"?: string;
}

export function StreamingText(data: StreamingTextProps) {
  const textRef = useRef<HTMLPreElement>(null);

  useRTVIClientEvent(
    RTVIEvent.ServerMessage,
    useCallback((message: StreamingTextProps) => {
      console.log("Server message:", message);
      if (!textRef.current) return;
      if (message["clear-pre-text"] === true) {
        textRef.current.textContent = "";
      }
      if (message["display-pre-text"]) {
        textRef.current.textContent += message["display-pre-text"];
      }
      textRef.current.scrollTop = textRef.current.scrollHeight;
    }, [])
  );

  const handleClear = () => {
    if (textRef.current) {
      textRef.current.textContent = '';
    }
  };

  return (
    <div className="text-stream">
      <pre ref={textRef} style={{ backgroundColor: data.bgColor || 'black' }} />
      <button onClick={handleClear}>Clear</button>
    </div>
  );
}
