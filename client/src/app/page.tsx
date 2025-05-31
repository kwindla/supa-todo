'use client';

import { RTVIClientAudio } from '@pipecat-ai/client-react';
import { ConnectButton } from '../components/ConnectButton';
import { MicToggleButton } from '../components/MicToggleButton';
import { StatusDisplay } from '../components/StatusDisplay';
import { DebugDisplay } from '../components/DebugDisplay';
import { StreamingDisplay } from '../components/StreamingDisplay';

export default function Home() {
  return (
    <div className="app">
      <div className="status-bar">
        <StatusDisplay />
        <div className="status-controls">
          <MicToggleButton />
          <ConnectButton />
        </div>
      </div>

      <div className="main-content">
        <StreamingDisplay />
      </div>

      <DebugDisplay />
      <RTVIClientAudio />
    </div>
  );
}
