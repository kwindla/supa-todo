'use client';

import { useCallback, useRef, useState, useEffect } from 'react';
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
  const [showText, setShowText] = useState(true);
  const [iframeCode, setIframeCode] = useState<string | null>(null);
  const [preText, setPreText] = useState('');

  const handleClear = () => {
    setPreText('');
    setShowText(true);
  };

  const handleMessage = useCallback((message: ServerMessage) => {
    if (message['clear-pre-text'] === true) {
      setPreText('');
      setShowText(true);
      return;
    }

    if (typeof message['display-pre-text'] === 'string') {
      setPreText(prev => prev + message['display-pre-text']);
      setShowText(true);
      return;
    }

    if (message['web-application-start']) {
      codeBuffer.current = '';
      setPreText('');
      setShowText(true);
      return;
    }

    if (typeof message['web-application-thinking'] === 'string') {
      setPreText(prev => prev + message['web-application-thinking']);
      return;
    }

    if (typeof message['web-application-code'] === 'string') {
      setPreText(prev => prev + message['web-application-code']);
      codeBuffer.current += message['web-application-code'];
      setShowText(true);
      return;
    }

    if (message['web-application-end']) {
      // strip ```html from the beginning of the buffer if needed
      if (codeBuffer.current.startsWith('```html')) {
        codeBuffer.current = codeBuffer.current.slice('```html'.length);
      }
      // strip ``` from the end of the buffer if needed
      if (codeBuffer.current.endsWith('```')) {
        codeBuffer.current = codeBuffer.current.slice(0, -3);
      }
      console.log("setting iframe code to:", codeBuffer.current);
      setIframeCode(codeBuffer.current);
      setShowText(false);
      setPreText('');
      return;
    }
  }, []);

  useRTVIClientEvent(RTVIEvent.ServerMessage, handleMessage);

  // Scroll <pre> to bottom when preText changes and <pre> is shown
  // This effect ensures scrolling even after remount
  useEffect(() => {
    if (showText && textRef.current) {
      textRef.current.scrollTop = textRef.current.scrollHeight;
    }
  }, [preText, showText]);

  return (
    <div className="text-stream">
      {showText ? (
        <>
          <pre ref={textRef} style={{ backgroundColor: 'black' }}>{preText}</pre>
          <button onClick={handleClear}>Clear</button>
        </>
      ) : (
        <GeneratedCodeIframe code={iframeCode ?? ''} />
      )}
    </div>
  );
}
