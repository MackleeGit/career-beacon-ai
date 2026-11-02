// src/components/Skeleton.jsx
import React from 'react';

export function Skeleton({ width = '100%', height = '16px', radius = 'var(--r-xs)', className = '', style }) {
  return (
    <div
      aria-hidden="true"
      className={`skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius: radius,
        ...style,
      }}
    />
  );
}

export function FeedCardSkeleton({ count = 3 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }} aria-busy="true" aria-label="Loading learning recommendations">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="lesson-card">
          <div className="lesson-card__grid">
            <div className="lesson-card__thumb" style={{ padding: '18px' }}>
              <Skeleton width="100%" height="100%" radius="var(--r-sm)" style={{ minHeight: '110px' }} />
            </div>
            <div className="lesson-card__body">
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <Skeleton width="80px" height="18px" />
                <Skeleton width="110px" height="18px" />
              </div>
              <Skeleton width="65%" height="22px" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <Skeleton width="90%" height="13px" />
                <Skeleton width="80%" height="13px" />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px' }}>
                <Skeleton width="130px" height="30px" radius="var(--r-sm)" />
                <Skeleton width="130px" height="30px" radius="var(--r-sm)" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function MentorCardSkeleton({ count = 3 }) {
  return (
    <div
      style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}
      aria-busy="true"
      aria-label="Loading mentor matches"
    >
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <Skeleton width="110px" height="20px" />
            <Skeleton width="70px" height="18px" />
          </div>
          <Skeleton width="52%" height="20px" style={{ marginBottom: '6px' }} />
          <Skeleton width="76%" height="14px" style={{ marginBottom: '14px' }} />
          <Skeleton width="100%" height="48px" radius="var(--r-sm)" style={{ marginBottom: '12px' }} />
          <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
            <Skeleton width="64px" height="20px" />
            <Skeleton width="78px" height="20px" />
            <Skeleton width="58px" height="20px" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
            <Skeleton width="110px" height="14px" />
            <Skeleton width="120px" height="30px" radius="var(--r-sm)" />
          </div>
        </div>
      ))}
    </div>
  );
}
