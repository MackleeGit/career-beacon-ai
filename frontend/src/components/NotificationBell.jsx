// src/components/NotificationBell.jsx
import { useState, useEffect, useRef, useMemo } from 'react';
import { Bell, Calendar, Users, MessageSquare, Video, CheckCircle2, X } from './Icons';

/**
 * Universal Notification Utility for Learner & Mentor Dashboards.
 * Automatically computes:
 * 1. Upcoming session reminders (<48h) with direct Jitsi video call buttons.
 * 2. Connection request / acceptance alerts.
 * 3. Recent message / booking activity.
 * 4. Periodic 60s countdown checks for sessions starting within 30 minutes.
 */
export default function NotificationBell({
  role = 'learner', // 'learner' | 'mentor'
  sessions = [],
  connections = [],
  onNavigate,
  onNotifyToast,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [dismissedIds, setDismissedIds] = useState(() => {
    try {
      const raw = localStorage.getItem(`cb_dismissed_notifs_${role}`);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const dropdownRef = useRef(null);
  const alertedUpcomingRef = useRef(new Set());

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  // Save dismissed notifications to localStorage
  const dismissNotification = (id) => {
    setDismissedIds((prev) => {
      const next = [...new Set([...prev, id])];
      try {
        localStorage.setItem(`cb_dismissed_notifs_${role}`, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const clearAllNotifications = () => {
    const allIds = activeNotifications.map((n) => n.id);
    setDismissedIds((prev) => {
      const next = [...new Set([...prev, ...allIds])];
      try {
        localStorage.setItem(`cb_dismissed_notifs_${role}`, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  // Derive notifications from live sessions and connections
  const activeNotifications = useMemo(() => {
    const list = [];
    const now = new Date();

    // 1. Session Notifications
    sessions.forEach((sess) => {
      if (sess.status === 'cancelled' || sess.status === 'completed') return;

      const startTime = new Date(sess.slot_start_iso);
      const diffMs = startTime - now;
      const diffHours = diffMs / (1000 * 60 * 60);

      // Session upcoming within next 48 hours
      if (diffHours > -0.75 && diffHours <= 48) {
        const isUrgent = diffHours <= 2;
        const timeLabel =
          diffHours < 0
            ? 'In Progress Now'
            : diffHours < 1
            ? `Starts in ${Math.max(1, Math.round(diffMs / 60000))} minutes`
            : `In ${Math.round(diffHours)} hours`;

        const otherParty =
          role === 'learner'
            ? sess.mentor_name || 'Mentor'
            : sess.learner_name || 'Mentee';

        list.push({
          id: `sess-${sess.id}`,
          type: 'session',
          priority: isUrgent ? 'high' : 'normal',
          title: `1-on-1 Session · ${timeLabel}`,
          body: `"${sess.topic}" with ${otherParty}. Focus: ${sess.focus_skill || 'Career Roadmap'}.`,
          meetingUrl: sess.meeting_url,
          timestamp: startTime.toISOString(),
          timeLabel,
        });
      }
    });

    // 2. Connection Notifications
    connections.forEach((conn) => {
      if (role === 'mentor' && conn.status === 'pending') {
        const learnerName = conn.learner_snapshot?.learner_name || 'A learner';
        list.push({
          id: `conn-pending-${conn.id}`,
          type: 'connection',
          priority: 'high',
          title: 'New Connection Request',
          body: `${learnerName} requested mentorship in ${conn.learner_snapshot?.target_career || 'your discipline'}.`,
          tab: 'roster',
          timestamp: conn.created_at,
        });
      } else if (role === 'learner' && conn.status === 'accepted') {
        const mentorName = conn.mentor?.full_name || 'Your mentor';
        list.push({
          id: `conn-accepted-${conn.id}`,
          type: 'connection',
          priority: 'normal',
          title: 'Connection Accepted',
          body: `${mentorName} accepted your connection request. Direct messaging & 1:1 scheduling are now active.`,
          tab: 'mentorship',
          timestamp: conn.updated_at || conn.created_at,
        });
      }
    });

    // Filter out dismissed notifications
    return list.filter((n) => !dismissedIds.includes(n.id));
  }, [sessions, connections, role, dismissedIds]);

  // Periodic alert: every 60s check if a session is starting within 30 minutes
  useEffect(() => {
    const checkUrgentSessions = () => {
      const now = new Date();
      sessions.forEach((sess) => {
        if (sess.status === 'cancelled' || sess.status === 'completed') return;
        const startTime = new Date(sess.slot_start_iso);
        const diffMs = startTime - now;
        const diffMinutes = Math.round(diffMs / 60000);

        if (diffMinutes > 0 && diffMinutes <= 30 && !alertedUpcomingRef.current.has(sess.id)) {
          alertedUpcomingRef.current.add(sess.id);
          if (onNotifyToast) {
            onNotifyToast(
              `Reminder: 1-on-1 Session "${sess.topic}" starts in ${diffMinutes} minutes!`
            );
          }
        }
      });
    };

    checkUrgentSessions();
    const interval = setInterval(checkUrgentSessions, 60000);
    return () => clearInterval(interval);
  }, [sessions, onNotifyToast]);

  const unreadCount = activeNotifications.length;

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={() => setIsOpen((o) => !o)}
        title="Notifications & Session Reminders"
        aria-label="Open notifications"
        style={{
          position: 'relative',
          padding: '6px 8px',
          color: unreadCount > 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
        }}
      >
        <Bell size={17} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '2px',
              right: '2px',
              minWidth: '17px',
              height: '17px',
              borderRadius: '9px',
              background: 'var(--accent)',
              color: '#ffffff',
              fontSize: '0.66rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 4px',
              boxShadow: '0 0 0 2px var(--surface)',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Floating Notification Dropdown Panel */}
      {isOpen && (
        <div
          role="region"
          aria-label="Notifications panel"
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: 'min(380px, calc(100vw - 32px))',
            maxHeight: '480px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-md)',
            boxShadow: 'var(--shadow-xl)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'var(--surface-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                Notifications
              </span>
              {unreadCount > 0 && (
                <span className="badge badge--accent" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                className="btn btn--ghost btn--xs"
                onClick={clearAllNotifications}
                style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}
              >
                Clear all
              </button>
            )}
          </div>

          {/* Notification List */}
          <div style={{ overflowY: 'auto', flex: 1, padding: '6px' }}>
            {activeNotifications.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={24} style={{ margin: '0 auto 8px', color: 'var(--status-success)' }} />
                <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  You&apos;re all caught up!
                </div>
                <div style={{ fontSize: '0.76rem', marginTop: '2px' }}>
                  No pending session alerts or unread connection requests.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {activeNotifications.map((notif) => {
                  const isHigh = notif.priority === 'high';
                  return (
                    <div
                      key={notif.id}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--r-sm)',
                        background: isHigh ? 'var(--accent-soft)' : 'var(--surface-subtle)',
                        border: '1px solid',
                        borderColor: isHigh ? 'var(--accent-border)' : 'var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {notif.type === 'session' ? (
                            <Calendar size={13} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                          ) : (
                            <Users size={13} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                          )}
                          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {notif.title}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="btn btn--ghost btn--xs"
                          onClick={() => dismissNotification(notif.id)}
                          style={{ padding: '2px', color: 'var(--text-muted)' }}
                          aria-label="Dismiss"
                        >
                          <X size={12} />
                        </button>
                      </div>

                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                        {notif.body}
                      </div>

                      {/* Action Links */}
                      <div style={{ display: 'flex', gap: '6px', marginTop: '2px' }}>
                        {notif.meetingUrl && (
                          <a
                            href={notif.meetingUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn--primary btn--xs"
                            style={{ gap: '4px', textDecoration: 'none' }}
                          >
                            <Video size={11} />
                            <span>Join Video Call</span>
                          </a>
                        )}
                        {notif.tab && onNavigate && (
                          <button
                            type="button"
                            className="btn btn--secondary btn--xs"
                            onClick={() => {
                              onNavigate(notif.tab);
                              setIsOpen(false);
                            }}
                          >
                            View Details
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
