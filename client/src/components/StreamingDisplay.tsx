'use client';

import { useCallback, useRef, useState } from 'react';
import { RTVIEvent } from '@pipecat-ai/client-js';
import { useRTVIClientEvent } from '@pipecat-ai/client-react';
import { GeneratedCodeIframe } from './GeneratedCodeIframe';

interface ServerMessage {
  'clear-pre-text'?: boolean;
  'display-pre-text'?: string;
  'web-application-start'?: boolean;
  'web-application-thinking'?: string;
  'web-application-code'?: string;
  'web-application-end'?: boolean;
}

export function StreamingDisplay() {
  const textRef = useRef<HTMLPreElement>(null);
  const codeBuffer = useRef<string>('');
  const [iframeCode, setIframeCode] = useState<string | null>(null);

  const handleClear = () => {
    if (textRef.current) {
      textRef.current.textContent = '';
    }
  };

  const showText = iframeCode === null;

  const handleMessage = useCallback((message: ServerMessage) => {
    if (!textRef.current) return;

    if (message['clear-pre-text'] === true) {
      setIframeCode(null);
      textRef.current.textContent = '';
      return;
    }

    if (typeof message['display-pre-text'] === 'string') {
      setIframeCode(null);
      textRef.current.textContent += message['display-pre-text'];
      textRef.current.scrollTop = textRef.current.scrollHeight;
      return;
    }

    if (message['web-application-start']) {
      setIframeCode(null);
      codeBuffer.current = '';
      textRef.current.textContent = '';
      return;
    }

    if (typeof message['web-application-thinking'] === 'string') {
      textRef.current.textContent += message['web-application-thinking'];
      textRef.current.scrollTop = textRef.current.scrollHeight;
      return;
    }

    if (typeof message['web-application-code'] === 'string') {
      textRef.current.textContent += message['web-application-code'];
      codeBuffer.current += message['web-application-code'];
      textRef.current.scrollTop = textRef.current.scrollHeight;
      return;
    }

    if (message['web-application-end']) {
      setIframeCode(codeBuffer.current);
      return;
    }
  }, []);

  useRTVIClientEvent(RTVIEvent.ServerMessage, handleMessage);

  return (
    <div className="text-stream">
      {showText ? (
        <>
          <pre ref={textRef} style={{ backgroundColor: 'black' }} />
          <button onClick={handleClear}>Clear</button>
        </>
      ) : (
        <GeneratedCodeIframe code={iframeCode ?? ''} />
      )}
    </div>
  );
}
