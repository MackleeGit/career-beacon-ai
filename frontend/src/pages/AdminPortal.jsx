// src/pages/AdminPortal.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';
import {
  getAdminStats,
  getAdminPendingCareers,
  reviewAdminCareer,
  getAdminMentors,
  verifyAdminMentor,
  getAdminFlaggedContent,
  takeAdminModerationAction,
} from '../lib/api';
import ThemeSelector from '../components/ThemeSelector';
import Toast from '../components/Toast';
import {
  ShieldCheck,
  LayoutDashboard,
  Layers,
  Users,
  AlertTriangle,
  CheckCircle2,
  Menu,
  X,
  LogOut,
  RefreshCw,
  Search,
  Check,
  Trash2,
  Award,
} from '../components/Icons';

export default function AdminPortal({ user, onSignOut }) {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'taxonomy' | 'mentors' | 'moderation'
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [pendingCareers, setPendingCareers] = useState([]);
  const [mentors, setMentors] = useState([]);
  const [flaggedItems, setFlaggedItems] = useState([]);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [statsRes, careersRes, mentorsRes, flagsRes] = await Promise.all([
        getAdminStats(),
        getAdminPendingCareers(),
        getAdminMentors(),
        getAdminFlaggedContent(),
      ]);
      setStats(statsRes.stats || null);
      setPendingCareers(careersRes.pending_careers || []);
      setMentors(mentorsRes.mentors || []);
      setFlaggedItems(flagsRes.flagged_items || []);
    } catch (err) {
      console.error('Failed to load admin data:', err);
      setToastMessage('Failed to load system metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleApproveCareer = async (careerId, title) => {
    setActionInProgress(true);
    try {
      await reviewAdminCareer(careerId, 'approve');
      setToastMessage(`Career "${title}" approved and verified.`);
      setPendingCareers((prev) => prev.filter((c) => c.id !== careerId));
      if (stats) setStats({ ...stats, unreviewed_careers: Math.max(0, stats.unreviewed_careers - 1) });
    } catch (err) {
      setToastMessage(err.message || 'Failed to approve career.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRejectCareer = async (careerId, title) => {
    setActionInProgress(true);
    try {
      await reviewAdminCareer(careerId, 'reject');
      setToastMessage(`Career "${title}" rejected and archived.`);
      setPendingCareers((prev) => prev.filter((c) => c.id !== careerId));
    } catch (err) {
      setToastMessage(err.message || 'Failed to reject career.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleToggleMentorVerify = async (mentorId, currentStatus) => {
    setActionInProgress(true);
    try {
      const nextStatus = !currentStatus;
      await verifyAdminMentor(mentorId, nextStatus);
      setMentors((prev) =>
        prev.map((m) => (m.mentor_id === mentorId ? { ...m, is_verified: nextStatus } : m))
      );
      setToastMessage(nextStatus ? 'Verified badge granted.' : 'Verified badge revoked.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to update verification.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleModerationAction = async (itemId, action, itemType) => {
    setActionInProgress(true);
    try {
      await takeAdminModerationAction(action, itemId, itemType);
      setFlaggedItems((prev) => prev.filter((f) => f.id !== itemId));
      setToastMessage(action === 'dismiss' ? 'Flag dismissed.' : 'Content deleted & record updated.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to perform moderation action.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    if (onSignOut) onSignOut();
  };

  return (
    <div className="app-shell" style={{ display: 'flex', minHeight: '100vh', background: 'var(--background)' }}>
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="app-sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Admin Sidebar */}
      <aside className={`app-sidebar ${mobileMenuOpen ? 'app-sidebar--mobile-open' : ''}`} style={{ width: '260px' }}>
        <div className="app-sidebar__header">
          <div className="logo-mark">
            <div className="logo-mark__icon" style={{ background: 'var(--accent)' }}>
              <ShieldCheck size={18} style={{ color: '#fff' }} />
            </div>
            <span style={{ fontWeight: 700 }}>Admin Console</span>
          </div>

          <button
            type="button"
            className="btn btn--ghost btn--sm mobile-menu-btn"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
            style={{ padding: '4px' }}
          >
            <X size={16} />
          </button>
        </div>

        <nav className="app-sidebar__nav" aria-label="Admin Navigation">
          <div className="app-sidebar__section-label">Operations</div>
          <button
            type="button"
            className={`nav-item ${activeTab === 'overview' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('overview');
              setMobileMenuOpen(false);
            }}
          >
            <LayoutDashboard size={17} className="nav-item__icon" />
            <span>Overview &amp; Metrics</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'taxonomy' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('taxonomy');
              setMobileMenuOpen(false);
            }}
          >
            <Layers size={17} className="nav-item__icon" />
            <span style={{ flex: 1 }}>Taxonomy Review</span>
            {pendingCareers.length > 0 && (
              <span className="nav-item__badge" style={{ background: 'var(--status-warning)' }}>
                {pendingCareers.length}
              </span>
            )}
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'mentors' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('mentors');
              setMobileMenuOpen(false);
            }}
          >
            <Users size={17} className="nav-item__icon" />
            <span>Mentor Verification</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'moderation' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('moderation');
              setMobileMenuOpen(false);
            }}
          >
            <AlertTriangle size={17} className="nav-item__icon" />
            <span style={{ flex: 1 }}>Safety &amp; Moderation</span>
            {flaggedItems.length > 0 && (
              <span className="nav-item__badge" style={{ background: 'var(--status-danger)' }}>
                {flaggedItems.length}
              </span>
            )}
          </button>
        </nav>

        <div className="app-sidebar__footer">
          <div style={{ padding: '6px 8px', marginBottom: '4px' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Administrator
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {user?.email || 'admin@careerbeacon.internal'}
            </div>
          </div>

          <button
            type="button"
            className="nav-item"
            onClick={() => setShowLogoutToast(true)}
            style={{ color: 'var(--text-secondary)' }}
          >
            <LogOut size={16} className="nav-item__icon" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main Administrative Workspace */}
      <div className="app-main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <header className="app-topbar">
          <div className="app-topbar__left">
            <button
              type="button"
              className="topbar-sidebar-toggle"
              onClick={() => setMobileMenuOpen((o) => !o)}
              aria-label="Toggle navigation drawer"
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <span style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--font-display)' }}>
              Career Beacon System Governance
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              · Live Admin Command Center
            </span>
          </div>

          <div className="app-topbar__right" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={loadAdminData}
              disabled={loading}
              title="Refresh Metrics"
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
            <ThemeSelector />
          </div>
        </header>

        <main className="app-content" style={{ padding: '24px', flex: 1 }}>
          {/* TAB 1: OVERVIEW & SYSTEM HEALTH */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>System Health &amp; Activity Overview</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Platform telemetry across learner onboarding, mentor ecosystem engagement, and taxonomy induction.
                </p>
              </div>

              {/* KPI Metric Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
                <div className="card" style={{ padding: '18px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Registered Learners</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                    {stats?.learner_count ?? 0}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Active vocational profiles</div>
                </div>

                <div className="card" style={{ padding: '18px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Registered Mentors</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--accent)' }}>
                    {stats?.mentor_count ?? 0}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Industry advisors &amp; experts</div>
                </div>

                <div className="card" style={{ padding: '18px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>1-on-1 Sessions</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--status-success)' }}>
                    {stats?.total_sessions ?? 0}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {stats?.completed_sessions ?? 0} completed &amp; reviewed
                  </div>
                </div>

                <div className="card" style={{ padding: '18px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Taxonomy Knowledge Base</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                    {stats?.total_careers ?? 0}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: stats?.unreviewed_careers ? 'var(--status-warning)' : 'var(--text-muted)', marginTop: '4px', fontWeight: 600 }}>
                    {stats?.unreviewed_careers ?? 0} pending review
                  </div>
                </div>
              </div>

              {/* Secondary Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div className="card">
                  <h3 style={{ fontSize: '1.02rem', marginBottom: '12px' }}>Mentorship Activity</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Accepted Mentee Connections</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{stats?.active_connections ?? 0}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Q&amp;A Hub Inquiries</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{stats?.total_questions ?? 0}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Verified Mentor Answers</span>
                      <strong style={{ color: 'var(--status-success)' }}>{stats?.answered_questions ?? 0}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: '0.86rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Mentor Pulse Feed Posts</span>
                      <strong style={{ color: 'var(--text-primary)' }}>{stats?.total_pulse_posts ?? 0}</strong>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <h3 style={{ fontSize: '1.02rem', marginBottom: '12px' }}>Academic Governance Summary</h3>
                  <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    The Career Beacon AI Engine operates on an <strong>Adaptive Occupational Induction Architecture</strong> with <strong>Human-by-Exception Governance</strong>. New career trajectories proposed or searched by users are provisionally induced with 8&ndash;10 testable vocational competencies, logged with provenance metadata (<code>source_origin: &apos;llm&apos;</code>), and queued for administrator verification.
                  </p>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    style={{ marginTop: '12px' }}
                    onClick={() => setActiveTab('taxonomy')}
                  >
                    Open Taxonomy Review Desk ({pendingCareers.length})
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TAXONOMY GOVERNANCE DESK */}
          {activeTab === 'taxonomy' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Career Taxonomy Governance</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Review, approve, or archive organically induced occupations and verify their 8&ndash;10 atomic vocational competencies.
                </p>
              </div>

              {pendingCareers.length === 0 ? (
                <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
                  <CheckCircle2 size={32} style={{ color: 'var(--status-success)', margin: '0 auto 10px' }} />
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '4px' }}>All Career Trajectories Verified</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    There are no unreviewed or pending career taxonomies awaiting approval.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {pendingCareers.map((c) => (
                    <div key={c.id} className="card" style={{ padding: '18px 22px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '12px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h3 style={{ fontSize: '1.12rem', margin: 0 }}>{c.title}</h3>
                            <span className="badge badge--warning">Unreviewed Induction</span>
                          </div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Origin: {c.source_origin} · Induced on {new Date(c.created_at).toLocaleDateString()}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            style={{ color: 'var(--status-danger)' }}
                            onClick={() => handleRejectCareer(c.id, c.title)}
                            disabled={actionInProgress}
                          >
                            <X size={14} />
                            <span>Reject &amp; Archive</span>
                          </button>
                          <button
                            type="button"
                            className="btn btn--primary btn--sm"
                            onClick={() => handleApproveCareer(c.id, c.title)}
                            disabled={actionInProgress}
                          >
                            <Check size={14} />
                            <span>Approve &amp; Verify</span>
                          </button>
                        </div>
                      </div>

                      {c.description && (
                        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                          {c.description}
                        </p>
                      )}

                      <div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                          Attached Vocational Competencies ({c.skills?.length || 0}):
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {(c.skills || []).map((s) => (
                            <span
                              key={s.id || s.name}
                              className="badge badge--neutral"
                              style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                            >
                              {s.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MENTOR CREDENTIAL VERIFICATION */}
          {activeTab === 'mentors' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Mentor Credential Verification</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Audit advisor profiles, inspect professional background credentials, and toggle the Gold Verified Mentor badge.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {mentors.map((m) => (
                  <div key={m.mentor_id} className="card" style={{ padding: '18px 22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div
                          style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--accent-soft)',
                            color: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                          }}
                        >
                          {m.full_name?.charAt(0) || 'M'}
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>{m.full_name}</h3>
                            {m.is_verified ? (
                              <span className="badge badge--success" style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                                <Award size={12} /> Verified Mentor
                              </span>
                            ) : (
                              <span className="badge badge--neutral">Standard Advisor</span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {m.headline || 'Industry Specialist'} · {m.primary_domain}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        className={`btn btn--sm ${m.is_verified ? 'btn--secondary' : 'btn--primary'}`}
                        onClick={() => handleToggleMentorVerify(m.mentor_id, m.is_verified)}
                        disabled={actionInProgress}
                      >
                        {m.is_verified ? 'Revoke Verified Badge' : 'Grant Verified Mentor Badge'}
                      </button>
                    </div>

                    {m.bio && (
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.45 }}>
                        {m.bio}
                      </p>
                    )}

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {(m.expertise_skills || []).map((sk) => (
                        <span key={sk} className="badge badge--neutral" style={{ fontSize: '0.72rem' }}>
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: SAFETY & CONTENT MODERATION */}
          {activeTab === 'moderation' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Safety &amp; Content Moderation</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Audit reported chat messages, spam links, and community pulse posts flagged by users.
                </p>
              </div>

              {flaggedItems.length === 0 ? (
                <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
                  <CheckCircle2 size={32} style={{ color: 'var(--status-success)', margin: '0 auto 10px' }} />
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '4px' }}>All Clear &ndash; No Flagged Content</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    There are no reported messages or suspicious content items pending administrator action.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {flaggedItems.map((item) => (
                    <div key={item.id} className="card" style={{ padding: '18px 22px', borderLeft: '4px solid var(--status-danger)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="badge badge--danger" style={{ textTransform: 'uppercase' }}>
                              {item.item_type} Report
                            </span>
                            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                              Context: {item.target_context}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                            Flagged for: {item.reason} · Reported {new Date(item.created_at).toLocaleString()}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => handleModerationAction(item.id, 'dismiss', item.item_type)}
                            disabled={actionInProgress}
                          >
                            Dismiss Report
                          </button>
                          <button
                            type="button"
                            className="btn btn--danger btn--sm"
                            onClick={() => handleModerationAction(item.id, 'delete', item.item_type)}
                            disabled={actionInProgress}
                          >
                            <Trash2 size={13} />
                            <span>Remove Content &amp; Warn</span>
                          </button>
                        </div>
                      </div>

                      <div
                        style={{
                          padding: '10px 14px',
                          background: 'var(--surface-subtle)',
                          borderRadius: 'var(--r-sm)',
                          fontSize: '0.84rem',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--status-danger)',
                        }}
                      >
                        &ldquo;{item.content_snippet}&rdquo;
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {toastMessage && (
        <Toast
          message={toastMessage}
          onClose={() => setToastMessage(null)}
        />
      )}

      {showLogoutToast && (
        <Toast
          message="Are you sure you want to sign out of the Admin Console?"
          confirmLabel="Sign out"
          onConfirm={handleSignOut}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </div>
  );
}

