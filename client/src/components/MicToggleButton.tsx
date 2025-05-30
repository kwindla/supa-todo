'use client';
import { useCallback, useEffect, useState } from 'react';
import { useRTVIClient } from '@pipecat-ai/client-react';

export function MicToggleButton() {
  const client = useRTVIClient();
  const [micEnabled, setMicEnabled] = useState(true);

  useEffect(() => {
    if (!client) return;
    const track = client.tracks().local.audio as MediaStreamTrack | undefined;
    if (track) {
      setMicEnabled(track.enabled);
    }
  }, [client]);

  const handleClick = useCallback(async () => {
    if (!client) return;
    const newState = !micEnabled;
    try {
      await client.enableMic(newState);
      setMicEnabled(newState);
    } catch (error) {
      console.error('Failed to toggle mic:', error);
    }
  }, [client, micEnabled]);

  return (
    <div className="controls">
      <button
        className={micEnabled ? 'mic-enabled' : 'mic-disabled'}
        onClick={handleClick}
        disabled={!client || !client.tracks().local.audio}
      >
        {micEnabled ? 'Mute Mic' : 'Unmute Mic'}
      </button>
    </div>
  );
}
