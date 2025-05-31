'use client';

import { useCallback, useRef } from 'react';
import { RTVIEvent } from '@pipecat-ai/client-js';
import { useRTVIClientEvent } from '@pipecat-ai/client-react';

interface StreamingTextProps {
  bgColor?: string;
}

export function StreamingText({ bgColor = 'black' }: StreamingTextProps) {
  const textRef = useRef<HTMLPreElement>(null);

  useRTVIClientEvent(
    RTVIEvent.ServerMessage,
    useCallback((data: any) => {
      console.log("Server message:", data);
      if (!textRef.current) return;
      textRef.current.textContent += JSON.stringify(data);
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
      <pre ref={textRef} style={{ backgroundColor: bgColor }} />
      <button onClick={handleClear}>Clear</button>
    </div>
  );
}
