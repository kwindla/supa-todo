'use client';

import { useEffect, useRef } from 'react';

interface GeneratedCodeIframeProps {
  code: string;
}

export function GeneratedCodeIframe({ code }: GeneratedCodeIframeProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!iframeRef.current) return;
    const doc = iframeRef.current.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(code);
    doc.close();
  }, [code]);

  return (
    <iframe
      ref={iframeRef}
      className="generated-iframe"
      sandbox="allow-scripts allow-same-origin"
    />
  );
}
