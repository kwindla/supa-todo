'use client';
import { useCallback, useEffect, useState } from 'react';
import { RTVIEvent, TransportState } from '@pipecat-ai/client-js';
import { useRTVIClient, useRTVIClientEvent } from '@pipecat-ai/client-react';

export function MicToggleButton() {
  const client = useRTVIClient();

  const [isMicEnabled, setIsMicEnabled] = useState(
    client?.isMicEnabled ?? false
  );
  const [isEnabled, setIsEnabled] = useState(client?.connected ?? false);

  // todo: fix this to sync initial state rather than just assuming initial state is mic enabled
  useEffect(() => {
    setIsMicEnabled(true);
  }, [client]);

    useRTVIClientEvent(
      RTVIEvent.TransportStateChanged,
      useCallback(
        (state: TransportState) => {
          console.log(`Transport state changed: ${state}`);
          setIsEnabled(state === 'connected' || state === 'ready');
        },
        []
      )
    );


  const handleClick = useCallback(async () => {
    setIsMicEnabled(!isMicEnabled);
    await client?.enableMic?.(!isMicEnabled);
  }, [client, isMicEnabled]);

  return (
    <div className="controls">
      <button
        className={isMicEnabled ? 'mic-enabled' : 'mic-disabled'}
        onClick={handleClick}
        disabled={!isEnabled}
      >
        {isMicEnabled ? 'Mute Mic' : 'Unmute Mic'}
      </button>
    </div>
  );
}
