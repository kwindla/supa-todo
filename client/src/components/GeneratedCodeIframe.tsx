'use client';

import React from 'react';

interface GeneratedCodeIframeProps {
  code: string;
}

export function GeneratedCodeIframe({ code }: GeneratedCodeIframeProps) {
  console.log("Generated code:", code);
  return (
    <iframe
      className="generated-iframe"
      sandbox="allow-scripts"
      srcDoc={code}
      title="Generated Code Preview"
    />
  );
}
