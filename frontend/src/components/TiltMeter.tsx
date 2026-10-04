import { useEffect, useRef, useState } from 'react';
import { startSlopeAngleListener } from '../lib/deviceSensors';

interface Props {
  angle: number;
  onChange: (deg: number) => void;
}

// SVG gauge constants
const CX = 100, CY = 105, R = 78;

/** Convert slope degrees (0–90) to an [x, y] point on the gauge arc. */
function gaugePoint(slopeDeg: number, r = R): [number, number] {
  // Maps slope 0 -> left (pi), slope 90 -> right (0)
  const rad = (1 - slopeDeg / 90) * Math.PI;
  return [CX + r * Math.cos(rad), CY - r * Math.sin(rad)];
}

/** SVG arc path string between two slope angles. */
function arcPath(a1: number, a2: number, r = R): string {
  const [x1, y1] = gaugePoint(a1, r);
  const [x2, y2] = gaugePoint(a2, r);
  // sweep=0: counter-clockwise in SVG = traces the upper semicircle
  const largeArc = (a2 - a1) / 90 * 180 > 180 ? 1 : 0;
  return `M ${x1.toFixed(1)},${y1.toFixed(1)} A ${r},${r} 0 ${largeArc},0 ${x2.toFixed(1)},${y2.toFixed(1)}`;
}

export default function TiltMeter({ angle, onChange }: Props) {
  const [live, setLive] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    startSlopeAngleListener((deg) => onChange(Math.min(89, Math.max(1, deg)))).then((fn) => {
      if (fn) { cleanupRef.current = fn; setLive(true); }
    });
    return () => { cleanupRef.current?.(); };
  }, []);

  const a = Math.min(89, Math.max(1, angle));
  const [nx, ny] = gaugePoint(a, 62);
  const color =
    a < 30 ? 'var(--color-stable)' :
    a < 50 ? 'var(--color-marginal)' :
             'var(--color-critical)';

  return (
    <div style={{ textAlign: 'center' }}>
      <svg
        viewBox="0 0 200 118"
        style={{ width: '100%', maxWidth: 260 }}
        aria-label={`Slope angle gauge showing ${a} degrees`}
      >
        {/* Background track */}
        <path
          d={arcPath(0, 89)}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        {/* Colour zone shading */}
        <path d={arcPath(0,  30)} fill="none" stroke="var(--color-stable)"   strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        <path d={arcPath(30, 50)} fill="none" stroke="var(--color-marginal)" strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        <path d={arcPath(50, 89)} fill="none" stroke="var(--color-critical)" strokeWidth="12" strokeLinecap="round" opacity="0.3" />
        {/* Active fill up to current angle */}
        {a > 0 && (
          <path d={arcPath(0, a)} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round" />
        )}
        {/* Needle */}
        <line
          x1={CX} y1={CY}
          x2={nx.toFixed(1)} y2={ny.toFixed(1)}
          stroke={color} strokeWidth="3" strokeLinecap="round"
        />
        <circle cx={CX} cy={CY} r="6" fill={color} />
        <circle cx={nx.toFixed(1)} cy={ny.toFixed(1)} r="3.5" fill={color} />
        {/* Zone labels at arc midpoints */}
        {([
          [15, 'SAFE'],
          [40, 'WARN'],
          [70, 'RISK'],
        ] as [number, string][]).map(([deg, label]) => {
          const [lx, ly] = gaugePoint(deg, R + 14);
          return (
            <text
              key={label}
              x={lx.toFixed(1)} y={ly.toFixed(1)}
              textAnchor="middle" dominantBaseline="middle"
              fontSize="7" fill="rgba(255,255,255,0.4)" fontWeight="600"
            >
              {label}
            </text>
          );
        })}
        {/* Large angle readout */}
        <text
          x={CX} y={CY + 16}
          textAnchor="middle"
          fontSize="20" fontWeight="700"
          fill={color}
        >
          {a}&deg;
        </text>
      </svg>

      {live ? (
        <p style={{ fontSize: '0.72rem', color: 'var(--color-sage)', margin: '2px 0 6px' }}>
          Live tilt — hold phone flat against slope face
        </p>
      ) : (
        <div style={{ margin: '6px 0' }}>
          <input
            type="range" min={1} max={89} value={a}
            onChange={(e) => onChange(Number(e.target.value))}
          />
          <p style={{ fontSize: '0.72rem', color: 'var(--color-text-dim)', margin: '2px 0 0' }}>
            Drag to set slope angle
          </p>
        </div>
      )}
    </div>
  );
}
