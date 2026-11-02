export function AvailabilitySignal({ bars }: { bars: number | null }) {
  return (
    <svg className={`availability-signal ${bars === null ? 'signal-unknown' : ''}`}
      viewBox="0 0 24 20" width="24" height="20" role="img"
      aria-label={bars === null ? 'Availability not yet known' : `Estimated availability: ${bars} of 4 bars`}>
      {[5, 9, 13, 18].map((height, index) => (
        <rect key={height} x={index * 6} y={20 - height} width="4" height={height}
          rx="1" fill="currentColor" opacity={bars !== null && index < bars ? 1 : 0.2} />
      ))}
    </svg>
  );
}
