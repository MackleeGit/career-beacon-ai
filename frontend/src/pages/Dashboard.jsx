// src/pages/Dashboard.jsx
import { useState, useEffect, useMemo } from 'react';
import { supabase } from '../lib/SupabaseClient';
import {
  getRecommendations,
  resetLearnerAccount,
  getMentorshipConnections,
  getMentorshipSessions,
} from '../lib/api';
import Toast from '../components/Toast';
import ThemeSelector from '../components/ThemeSelector';
import NotificationBell from '../components/NotificationBell';
import { Skeleton } from '../components/Skeleton';
import Recommendations from './Recommendations';
import LearnerMentorship from './LearnerMentorship';
import {
  Compass,
  LayoutDashboard,
  BookOpen,
  Layers,
  Bookmark,
  Users,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  X,
  LogOut,
  CheckCircle2,
  ShieldCheck,
  ArrowRight,
  Search,
  Clock,
  RotateCcw,
  AlertTriangle,
  User,
} from '../components/Icons';

function getLevelMeta(score) {
  if (score >= 100) {
    return { label: 'Mastered', badgeClass: 'badge--success' };
  }
  if (score >= 80) {
    return { label: 'Advanced', badgeClass: 'badge--accent' };
  }
  if (score >= 50) {
    return { label: 'Working', badgeClass: 'badge--warning' };
  }
  return { label: 'Foundational', badgeClass: 'badge--neutral' };
}

function SkillCard({ skill, onFocusSkill }) {
  const { label, badgeClass } = getLevelMeta(skill.proficiency);
  const isMentorVerified =
    skill.evidence_source === 'mentor_verified' ||
    skill.evidence_source === 'diagnostic_assessment';
  const isEssential = skill.importance === 'essential' || (skill.importance_score ?? 0.8) >= 0.75;

  return (
    <div
      style={{
        padding: '14px 16px',
        background: 'var(--surface)',
        border: '1px solid',
        borderColor: isMentorVerified ? 'var(--accent-border)' : 'var(--border)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
            <span>{skill.name}</span>
            {isMentorVerified && (
              <span className="badge badge--accent" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                <ShieldCheck size={11} /> Verified
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {skill.category ? `${skill.category} · ` : ''}
            <span style={{ color: isEssential ? 'var(--text-secondary)' : 'var(--text-muted)', fontWeight: isEssential ? 500 : 400 }}>
              {isEssential ? 'Core requirement' : 'Supporting'}
            </span>
          </div>
        </div>
        <span className={`badge ${badgeClass}`}>{label}</span>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '5px' }}>
          <span>Proficiency</span>
          <strong className="mono" style={{ color: 'var(--text-primary)' }}>{skill.proficiency}%</strong>
        </div>
        <div className="progress-bar" style={{ height: '5px' }}>
          <div className="progress-bar__fill" style={{ width: `${skill.proficiency}%` }} />
        </div>
      </div>

      {skill.proficiency < 100 && onFocusSkill && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'auto' }}>
          <button
            type="button"
            className="btn btn--ghost btn--xs"
            onClick={() => onFocusSkill(skill)}
            style={{ color: 'var(--accent)', padding: '3px 6px' }}
          >
            <span>Practice</span>
            <ArrowRight size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

export default function Dashboard({ user, career, skills = [], onSkillUpdated, onRecalibrateCareer }) {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'feed' | 'graph' | 'saved' | 'mentorship' | 'settings'
  const [feedInitialSubTab, setFeedInitialSubTab] = useState('daily');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [showLogoutToast, setShowLogoutToast] = useState(false);
  const [prefillMentorQuestion, setPrefillMentorQuestion] = useState(null);

  // Account Space state
  const [accountFullName, setAccountFullName] = useState(user?.user_metadata?.full_name || '');
  const [savingName, setSavingName] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [resettingAccount, setResettingAccount] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Connected Accounts / Integrations
  const isGoogleProvider = user?.app_metadata?.providers?.includes('google') || user?.email?.endsWith('@gmail.com');
  const [googleEmail, setGoogleEmail] = useState(
    user?.user_metadata?.google_email || (isGoogleProvider ? user?.email : '')
  );
  const [linkedinUrl, setLinkedinUrl] = useState(user?.user_metadata?.linkedin_url || '');
  const [githubHandle, setGithubHandle] = useState(user?.user_metadata?.github_username || '');
  const [savingIntegrations, setSavingIntegrations] = useState(false);

  const handleSaveIntegrations = async (e) => {
    e?.preventDefault();
    setSavingIntegrations(true);
    try {
      await supabase.auth.updateUser({
        data: {
          google_email: googleEmail.trim(),
          linkedin_url: linkedinUrl.trim(),
          github_username: githubHandle.trim(),
        },
      });
      setToastMessage('Connected accounts updated successfully.');
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err) {
      console.error('Failed to update integrations:', err);
      setToastMessage('Failed to update connected accounts.');
      setTimeout(() => setToastMessage(null), 3500);
    } finally {
      setSavingIntegrations(false);
    }
  };

  const handleToggleSidebar = () => {
    if (window.innerWidth <= 900) {
      setMobileMenuOpen(!mobileMenuOpen);
    } else {
      setSidebarCollapsed(!sidebarCollapsed);
    }
  };

  const handleSaveAccountProfile = async (e) => {
    e?.preventDefault();
    if (!accountFullName.trim()) return;
    setSavingName(true);
    try {
      await supabase.auth.updateUser({ data: { full_name: accountFullName.trim() } });
      await supabase.from('profiles').update({ full_name: accountFullName.trim() }).eq('id', user.id);
      setToastMessage('Profile name updated successfully.');
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err) {
      console.error('Failed to update profile name:', err);
      setToastMessage('Failed to update profile name.');
      setTimeout(() => setToastMessage(null), 3500);
    } finally {
      setSavingName(false);
    }
  };

  const handleConfirmResetLearnerAccount = async () => {
    setResettingAccount(true);
    try {
      await resetLearnerAccount();
      setShowResetModal(false);
      if (onRecalibrateCareer) {
        onRecalibrateCareer();
      } else {
        window.location.reload();
      }
    } catch (err) {
      console.error('Failed to reset learner account:', err);
      setToastMessage('Failed to reset account. Please try again.');
      setTimeout(() => setToastMessage(null), 4000);
      setResettingAccount(false);
    }
  };

  const [overviewFeed, setOverviewFeed] = useState({ recommendations: [], completed: [], loading: true });
  const [skillSearch, setSkillSearch] = useState('');
  const [skillFilter, setSkillFilter] = useState('all'); // 'all' | 'gaps' | 'mastered'

  useEffect(() => {
    let isMounted = true;
    async function loadOverviewSnapshot() {
      if (!user?.id || activeTab !== 'overview') return;
      try {
        const res = await getRecommendations(user.id, 4);
        if (isMounted) {
          setOverviewFeed({
            recommendations: (res.recommendations || []).slice(0, 3),
            completed: (res.completed_library || []).slice(0, 3),
            loading: false,
          });
        }
      } catch {
        if (isMounted) {
          setOverviewFeed((prev) => ({ ...prev, loading: false }));
        }
      }
    }
    loadOverviewSnapshot();
    return () => {
      isMounted = false;
    };
  }, [user?.id, skills, activeTab]);

  const [learnerSessions, setLearnerSessions] = useState([]);
  const [learnerConnections, setLearnerConnections] = useState([]);

  useEffect(() => {
    let isMounted = true;
    async function loadNotificationsData() {
      if (!user?.id) return;
      try {
        const [cRes, sRes] = await Promise.all([
          getMentorshipConnections('learner').catch(() => ({ connections: [] })),
          getMentorshipSessions('learner').catch(() => ({ sessions: [] })),
        ]);
        if (isMounted) {
          setLearnerConnections(cRes.connections || []);
          setLearnerSessions(sRes.sessions || []);
        }
      } catch {
        // silent fallback
      }
    }
    loadNotificationsData();
    const interval = setInterval(loadNotificationsData, 45000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user?.id, activeTab]);

  const handleSignOut = async () => {
    setSigningOut(true);
    setShowLogoutToast(false);
    await supabase.auth.signOut();
  };

  const handleAskMentorAboutLesson = (questionPayload) => {
    setPrefillMentorQuestion(questionPayload);
    setActiveTab('mentorship');
  };

  const navigateTo = (tab, subTab = 'daily') => {
    if (tab === 'feed') setFeedInitialSubTab(subTab);
    if (tab === 'saved') setFeedInitialSubTab('completed');
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Learner';

  // Compute importance-weighted career readiness
  const totalWeight = skills.reduce((sum, s) => {
    const w = s.importance_score ?? (s.importance === 'essential' ? 1.0 : s.importance === 'optional' ? 0.5 : 0.75);
    return sum + Math.max(0.2, w);
  }, 0);

  const weightedSum = skills.reduce((sum, s) => {
    const w = s.importance_score ?? (s.importance === 'essential' ? 1.0 : s.importance === 'optional' ? 0.5 : 0.75);
    return sum + s.proficiency * Math.max(0.2, w);
  }, 0);

  const avgProgress = skills.length && totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
  const masteredCount = skills.filter((s) => s.proficiency >= 100).length;
  const verifiedCount = skills.filter(
    (s) => s.evidence_source === 'mentor_verified' || s.evidence_source === 'diagnostic_assessment' || s.proficiency >= 80
  ).length;

  const priorityGaps = useMemo(
    () =>
      [...skills]
        .filter((s) => s.proficiency < 75)
        .sort((a, b) => a.proficiency - b.proficiency),
    [skills]
  );

  const filteredSkills = useMemo(() => {
    return skills.filter((s) => {
      const matchesQuery =
        !skillSearch.trim() ||
        s.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
        (s.category || '').toLowerCase().includes(skillSearch.toLowerCase());
      if (!matchesQuery) return false;
      if (skillFilter === 'gaps') return s.proficiency < 75;
      if (skillFilter === 'mastered') return s.proficiency >= 100;
      return true;
    });
  }, [skills, skillSearch, skillFilter]);

  const navItems = [
    { id: 'overview', domId: 'tab-overview', label: 'Overview', Icon: LayoutDashboard },
    { id: 'feed', domId: 'tab-learning-feed', label: 'Learning Feed', Icon: BookOpen },
    { id: 'graph', domId: 'tab-skill-graph', label: 'Skills & Progress', Icon: Layers, badge: skills.length },
    { id: 'saved', domId: 'tab-saved-library', label: 'Completed & Saved', Icon: Bookmark },
    { id: 'mentorship', domId: 'tab-mentorship-hub', label: 'Mentorship', Icon: Users },
    { id: 'settings', domId: 'tab-settings', label: 'Account & Settings', Icon: Settings },
  ];

  const activeNavMeta = navItems.find((item) => item.id === activeTab) || navItems[0];

  const renderSkillMatrixSection = (title = 'Your Skill Graph') => (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1.08rem', marginBottom: '2px' }}>{title}</h3>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {skills.length} competencies mapped to {career?.title || 'your target role'}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div className="segmented-tabs" role="tablist" aria-label="Filter skills">
            <button
              type="button"
              className={`segmented-tab ${skillFilter === 'all' ? 'segmented-tab--active' : ''}`}
              onClick={() => setSkillFilter('all')}
            >
              All <span className="segmented-tab__count">{skills.length}</span>
            </button>
            <button
              type="button"
              className={`segmented-tab ${skillFilter === 'gaps' ? 'segmented-tab--active' : ''}`}
              onClick={() => setSkillFilter('gaps')}
            >
              Gaps <span className="segmented-tab__count">{priorityGaps.length}</span>
            </button>
            <button
              type="button"
              className={`segmented-tab ${skillFilter === 'mastered' ? 'segmented-tab--active' : ''}`}
              onClick={() => setSkillFilter('mastered')}
            >
              Mastered <span className="segmented-tab__count">{masteredCount}</span>
            </button>
          </div>

          <div style={{ position: 'relative', width: '210px' }}>
            <Search
              size={14}
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}
            />
            <input
              type="search"
              className="input"
              placeholder="Filter skills..."
              value={skillSearch}
              onChange={(e) => setSkillSearch(e.target.value)}
              style={{ paddingLeft: '30px', paddingTop: '6px', paddingBottom: '6px', fontSize: '0.81rem' }}
            />
          </div>
        </div>
      </div>

      {filteredSkills.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '28px 0', fontSize: '0.88rem' }}>
          No skills match the selected filter.
        </p>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '12px',
          }}
        >
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              onFocusSkill={() => navigateTo('feed', 'daily')}
            />
          ))}
        </div>
      )}
    </section>
  );

  return (
    <div className="app-shell">
      {mobileMenuOpen && (
        <div
          className="app-sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Persistent Sidebar */}
      <aside
        className={`app-sidebar ${sidebarCollapsed ? 'app-sidebar--collapsed' : ''} ${mobileMenuOpen ? 'app-sidebar--mobile-open' : ''
          }`}
        aria-label="Primary Navigation"
      >
        <div className="app-sidebar__header">
          <div className="logo-mark" style={{ overflow: 'hidden' }}>
            <div className="logo-mark__icon">
              <Compass size={16} />
            </div>
            {!sidebarCollapsed && <span>Career Beacon</span>}
          </div>

          <button
            type="button"
            className="btn btn--ghost btn--sm desktop-collapse-btn"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{ padding: '5px' }}
          >
            {sidebarCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
        </div>

        {!sidebarCollapsed && (
          <div
            style={{
              margin: '12px 10px 4px',
              padding: '11px 12px',
              borderRadius: 'var(--r-sm)',
              background: 'var(--surface-subtle)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
              Target role
            </div>
            <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3, marginBottom: '8px' }}>
              {career?.title || 'Career Path'}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              <span>Readiness</span>
              <strong className="mono" style={{ color: 'var(--accent)' }}>{avgProgress}%</strong>
            </div>
            <div className="progress-bar" style={{ height: '4px' }}>
              <div className="progress-bar__fill" style={{ width: `${avgProgress}%` }} />
            </div>
          </div>
        )}

        <nav className="app-sidebar__nav" aria-label="Workspace sections">
          {!sidebarCollapsed && <div className="app-sidebar__section-label">Workspace</div>}
          {navItems.map(({ id, domId, label, Icon, badge }) => {
            const isActive = activeTab === id;
            return (
              <button
                key={id}
                id={domId}
                type="button"
                className={`nav-item ${isActive ? 'nav-item--active' : ''}`}
                onClick={() => navigateTo(id)}
                title={sidebarCollapsed ? label : undefined}
              >
                <Icon size={17} className="nav-item__icon" />
                {!sidebarCollapsed && <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>}
                {!sidebarCollapsed && badge !== undefined && (
                  <span className="nav-item__badge">{badge}</span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="app-sidebar__footer">
          {!sidebarCollapsed && (
            <div style={{ padding: '4px 8px', marginBottom: '2px' }}>
              <div style={{ fontSize: '0.81rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {displayName}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.email}
              </div>
            </div>
          )}
          <button
            id="sign-out-btn"
            type="button"
            className="nav-item"
            onClick={() => setShowLogoutToast(true)}
            disabled={signingOut}
            style={{ color: 'var(--text-secondary)' }}
            title="Sign out"
          >
            <LogOut size={16} className="nav-item__icon" />
            {!sidebarCollapsed && <span>{signingOut ? 'Signing out...' : 'Sign out'}</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="app-main">
        <header className="app-topbar">
          <div className="app-topbar__left">
            <button
              type="button"
              className="topbar-sidebar-toggle"
              onClick={handleToggleSidebar}
              aria-label="Toggle navigation menu"
              title="Toggle sidebar"
            >
              <Menu size={18} />
            </button>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 650, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>
                {activeNavMeta.label}
              </span>
              {career?.title && (
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  · {career.title}
                </span>
              )}
            </div>
          </div>

          <div className="app-topbar__right">
            <NotificationBell
              role="learner"
              sessions={learnerSessions}
              connections={learnerConnections}
              onNavigate={(tab) => navigateTo(tab)}
              onNotifyToast={setToastMessage}
            />
            <ThemeSelector />
            {activeTab !== 'feed' && (
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={() => navigateTo('feed', 'daily')}
              >
                <BookOpen size={14} />
                <span>Start Learning Sprint</span>
              </button>
            )}
          </div>
        </header>

        <main className="app-content">
          {activeTab === 'feed' ? (
            <Recommendations
              user={user}
              career={career}
              skills={skills}
              initialSubTab={feedInitialSubTab}
              onSkillUpdated={onSkillUpdated}
              onNavigateToGraph={() => navigateTo('graph')}
              onAskMentorAboutLesson={handleAskMentorAboutLesson}
            />
          ) : activeTab === 'saved' ? (
            <Recommendations
              user={user}
              career={career}
              skills={skills}
              initialSubTab="completed"
              onSkillUpdated={onSkillUpdated}
              onNavigateToGraph={() => navigateTo('graph')}
              onAskMentorAboutLesson={handleAskMentorAboutLesson}
            />
          ) : activeTab === 'mentorship' ? (
            <LearnerMentorship
              user={user}
              career={career}
              skills={skills}
              prefillQuestion={prefillMentorQuestion}
              onClearPrefillQuestion={() => setPrefillMentorQuestion(null)}
            />
          ) : activeTab === 'settings' ? (
            <div style={{ maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Profile Card */}
              <form className="card" onSubmit={handleSaveAccountProfile}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
                  <div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '50%',
                      background: 'var(--accent-soft)',
                      color: 'var(--accent)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '1.25rem',
                      fontWeight: 700,
                    }}
                  >
                    {displayName.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h2 style={{ fontSize: '1.25rem', margin: '0 0 2px' }}>Account &amp; Profile Information</h2>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0 }}>
                      Manage your personal identity, occupation goals, and theme preferences.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginBottom: '16px' }}>
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input
                      type="text"
                      className="input"
                      value={accountFullName}
                      onChange={(e) => setAccountFullName(e.target.value)}
                      placeholder="Your Full Name"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Registered Email</label>
                    <input
                      type="text"
                      className="input"
                      value={user?.email || ''}
                      disabled
                      style={{ opacity: 0.7, background: 'var(--surface-subtle)' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ padding: '12px 14px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
                      Target Occupation
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {career?.title || 'Not specified'}
                    </div>
                  </div>

                  <div style={{ padding: '12px 14px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
                      Tracked Competencies
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent)' }}>
                      {skills.length} skills ({masteredCount} mastered)
                    </div>
                  </div>

                  <div style={{ padding: '12px 14px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
                      Weighted Readiness
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent)' }}>
                      {avgProgress}%
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  <button
                    type="submit"
                    className="btn btn--primary btn--sm"
                    disabled={savingName || !accountFullName.trim()}
                  >
                    {savingName ? 'Saving Changes...' : 'Save Profile Changes'}
                  </button>
                </div>
              </form>

              {/* Connected Accounts & External Identity */}
              <form className="card" onSubmit={handleSaveIntegrations}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', margin: '0 0 4px' }}>Connected Accounts &amp; Verified Identity</h3>
                    <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', margin: 0 }}>
                      Connect your external platforms to enable Google Calendar synchronization, portfolio verification, and professional proof of work.
                    </p>
                  </div>
                  <span className="badge badge--success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={12} /> Jitsi Video Ready
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label className="form-label" style={{ margin: 0 }}>
                        Google Account (Optional Calendar Sync)
                      </label>
                      <span style={{ fontSize: '0.74rem', color: googleEmail ? 'var(--status-success)' : 'var(--text-muted)', fontWeight: 600 }}>
                        {googleEmail ? 'Active for Invites' : 'Optional'}
                      </span>
                    </div>
                    <input
                      type="email"
                      className="input"
                      placeholder="your.email@gmail.com"
                      value={googleEmail}
                      onChange={(e) => setGoogleEmail(e.target.value)}
                    />
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                      Mentorship session invites, video room calendar entries, and reminder alerts will sync to this Google address.
                    </div>
                  </div>

                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label" style={{ marginBottom: '4px' }}>
                      LinkedIn Profile URL (Professional Verification)
                    </label>
                    <input
                      type="url"
                      className="input"
                      placeholder="https://linkedin.com/in/yourprofile"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                    />
                  </div>

                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label" style={{ marginBottom: '4px' }}>
                      GitHub Username (Technical Portfolio &amp; Proof of Work)
                    </label>
                    <input
                      type="text"
                      className="input"
                      placeholder="e.g. octocat"
                      value={githubHandle}
                      onChange={(e) => setGithubHandle(e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  <button
                    type="submit"
                    className="btn btn--primary btn--sm"
                    disabled={savingIntegrations}
                  >
                    {savingIntegrations ? 'Saving Integrations...' : 'Save Connected Accounts'}
                  </button>
                </div>
              </form>

              {/* Preferences & Appearance Card */}
              <div className="card">
                <h3 style={{ fontSize: '1.05rem', marginBottom: '14px' }}>System &amp; Appearance</h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      Color Theme
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Switch between Light, Dark, or sync with your system preference.
                    </div>
                  </div>
                  <ThemeSelector showLabels size="md" />
                </div>

                {onRecalibrateCareer && (
                  <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                        Recalibrate Career &amp; Skills
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Choose a different occupation or adjust your baseline skill ratings without deleting your account history.
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={onRecalibrateCareer}
                    >
                      <RotateCcw size={14} /> Recalibrate Baseline
                    </button>
                  </div>
                )}
              </div>

              {/* Danger Zone Card */}
              <div className="danger-zone-card">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                  <div style={{ color: 'var(--status-danger)', marginTop: '2px' }}>
                    <AlertTriangle size={24} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ color: 'var(--status-danger)', fontSize: '1.02rem', margin: '0 0 4px' }}>
                      Danger Zone &ndash; Restart Learner Onboarding
                    </h4>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 14px', lineHeight: 1.5 }}>
                      Restarting your onboarding will permanently erase all lesson checkpoints, quiz scores, skill graph progress, mentor connections, and scheduled 1-on-1 sessions. You will be redirected to the career selection step. This action cannot be undone.
                    </p>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => setShowResetModal(true)}
                    >
                      <RotateCcw size={13} />
                      <span>Restart Learner Onboarding</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : activeTab === 'graph' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Skills &amp; Progress</h1>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    Pass 5-question lesson checkpoints or complete 1-on-1 mentor sessions to advance your proficiency for <strong style={{ color: 'var(--text-primary)' }}>{career?.title}</strong>.
                  </p>
                </div>
                {onRecalibrateCareer && (
                  <button type="button" className="btn btn--secondary btn--sm" onClick={onRecalibrateCareer}>
                    <RotateCcw size={14} /> Recalibrate Baseline
                  </button>
                )}
              </div>
              {renderSkillMatrixSection('All Tracked Competencies')}
            </div>
          ) : (
            /* OVERVIEW: Cohesive, non-repetitive command centre */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 1. Unified Career Summary + Inline KPI Strip */}
              <section className="card" style={{ padding: '22px 24px' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '16px',
                    marginBottom: '18px',
                  }}
                >
                  <div style={{ maxWidth: '640px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Hello, <strong style={{ color: 'var(--text-secondary)' }}>{displayName}</strong> · Target career
                    </div>
                    <h1 style={{ fontSize: 'clamp(1.35rem, 2.2vw, 1.7rem)', marginBottom: '6px' }}>
                      {career?.title ?? 'Career Development Plan'}
                    </h1>
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                      {career?.description ||
                        'Progress through targeted lessons, pass 5-question checkpoints, and work with industry mentors to close your skill gaps.'}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => navigateTo('mentorship')}
                    >
                      <Users size={14} />
                      <span>Match with a Mentor</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      onClick={() => navigateTo('feed', 'daily')}
                    >
                      <span>Start Micro-Learning Sprint</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>

                {/* Single Clean Inline KPI Strip (replaces duplicate hero box + 4 icon stat cards) */}
                <div className="kpi-strip">
                  <div className="kpi-strip__item">
                    <span className="kpi-strip__label">Weighted readiness</span>
                    <span className="kpi-strip__value" style={{ color: 'var(--accent)' }}>{avgProgress}%</span>
                    <div className="progress-bar" style={{ height: '4px', marginTop: '6px' }}>
                      <div className="progress-bar__fill" style={{ width: `${avgProgress}%` }} />
                    </div>
                  </div>

                  <div className="kpi-strip__item">
                    <span className="kpi-strip__label">Mastered skills</span>
                    <span className="kpi-strip__value">{masteredCount} <span style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ {skills.length}</span></span>
                    <span className="kpi-strip__sub">At 100% estimate</span>
                  </div>

                  <div className="kpi-strip__item">
                    <span className="kpi-strip__label">Priority gaps</span>
                    <span className="kpi-strip__value">{priorityGaps.length}</span>
                    <span className="kpi-strip__sub">Below 75% target</span>
                  </div>

                  <div className="kpi-strip__item">
                    <span className="kpi-strip__label">Strong / verified</span>
                    <span className="kpi-strip__value">{verifiedCount}</span>
                    <span className="kpi-strip__sub">80%+ or mentor-endorsed</span>
                  </div>
                </div>

                {/* Connected Identity Nudge if Google/LinkedIn is not yet linked */}
                {(!user?.user_metadata?.google_email && !user?.email?.endsWith('@gmail.com') && !user?.app_metadata?.providers?.includes('google')) && (
                  <div
                    style={{
                      marginTop: '16px',
                      padding: '12px 18px',
                      background: 'var(--surface-subtle)',
                      border: '1px solid var(--accent-border)',
                      borderRadius: 'var(--r-md)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '12px',
                      flexWrap: 'wrap',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <ShieldCheck size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                      <div>
                        <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          Verify Your Calendar &amp; Professional Identity
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          Connect your Google and LinkedIn accounts to enable 1-on-1 mentorship bookings and instant calendar invites.
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn btn--secondary btn--xs"
                      onClick={() => navigateTo('settings')}
                    >
                      Connect Accounts
                    </button>
                  </div>
                )}
              </section>

              {/* 2. Above-the-Fold Next Actions: Up Next in Feed + Lowest-Rated Skills */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '18px',
                }}
              >
                {/* Left: Recommended Next Lessons */}
                <section className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '8px' }}>
                    <div>
                      <h3 style={{ fontSize: '1rem' }}>Up Next in Your Sprint</h3>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Lessons queued for your highest-priority skill gaps
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs"
                      onClick={() => navigateTo('feed', 'daily')}
                      style={{ color: 'var(--accent)' }}
                    >
                      <span>Open feed</span>
                      <ArrowRight size={12} />
                    </button>
                  </div>

                  {overviewFeed.loading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <Skeleton height="56px" />
                      <Skeleton height="56px" />
                      <Skeleton height="56px" />
                    </div>
                  ) : overviewFeed.recommendations.length === 0 ? (
                    <div style={{ padding: '20px 14px', textAlign: 'center', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)' }}>
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                        Open your Learning Feed to complete today's Daily Focus Drop.
                      </p>
                      <button type="button" className="btn btn--primary btn--sm" onClick={() => navigateTo('feed', 'daily')}>
                        Open Learning Feed
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {overviewFeed.recommendations.map((item) => (
                        <div
                          key={item.id}
                          style={{
                            padding: '10px 12px',
                            borderRadius: 'var(--r-sm)',
                            background: 'var(--surface-subtle)',
                            border: '1px solid var(--border-subtle)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '12px',
                          }}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--accent)' }}>
                                {item.skill_name}
                              </span>
                              <span style={{ fontSize: '0.71rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                                <Clock size={11} /> {item.video_id ? '12 min video' : '8 min read'}
                              </span>
                            </div>
                            <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {item.title}
                            </div>
                          </div>
                          <button
                            type="button"
                            className="btn btn--secondary btn--xs"
                            onClick={() => navigateTo('feed', 'daily')}
                            style={{ flexShrink: 0 }}
                          >
                            Start
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                {/* Right: Priority Skill Gaps */}
                <section className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '8px' }}>
                    <div>
                      <h3 style={{ fontSize: '1rem' }}>Skills to Strengthen Next</h3>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Lowest-rated competencies with the largest impact on readiness
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs"
                      onClick={() => navigateTo('graph')}
                      style={{ color: 'var(--accent)' }}
                    >
                      <span>View all</span>
                      <ArrowRight size={12} />
                    </button>
                  </div>

                  {priorityGaps.length === 0 ? (
                    <div style={{ padding: '20px 14px', textAlign: 'center', background: 'var(--status-success-bg)', borderRadius: 'var(--r-sm)', border: '1px solid var(--status-success-bd)' }}>
                      <CheckCircle2 size={20} style={{ color: 'var(--status-success)', marginBottom: '4px' }} />
                      <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--status-success)' }}>
                        All tracked skills are at 75% proficiency or higher.
                      </p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {priorityGaps.slice(0, 4).map((gap) => (
                        <div
                          key={gap.id}
                          style={{
                            padding: '9px 12px',
                            borderRadius: 'var(--r-sm)',
                            background: 'var(--surface-subtle)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                            <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                              {gap.name}
                            </span>
                            <span className="mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                              {gap.proficiency}%
                            </span>
                          </div>
                          <div className="progress-bar" style={{ height: '4px' }}>
                            <div className="progress-bar__fill" style={{ width: `${gap.proficiency}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </div>

              {/* 3. Full Skill Graph Matrix */}
              {renderSkillMatrixSection('Your Skill Graph')}
            </div>
          )}
        </main>
      </div>

      {/* RESTART ONBOARDING CONFIRMATION MODAL */}
      {showResetModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.72)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 100,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '520px',
              width: '100%',
              padding: '24px',
              border: '1px solid var(--status-danger-bd)',
              boxShadow: 'var(--shadow-xl)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--status-danger)' }}>
              <AlertTriangle size={22} />
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Restart Onboarding &amp; Wipe Progress?</h3>
            </div>

            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '14px' }}>
              Are you sure you want to restart onboarding? You will <strong>lose all lesson checkpoint progress, quiz scores, skill masteries, mentor connections, and scheduled 1-on-1 sessions</strong>.
            </p>

            <div
              style={{
                padding: '12px',
                background: 'var(--status-danger-bg)',
                borderRadius: 'var(--r-sm)',
                border: '1px solid var(--status-danger-bd)',
                fontSize: '0.82rem',
                color: 'var(--status-danger)',
                marginBottom: '18px',
              }}
            >
              This action cannot be undone. You will immediately be routed back to Step 1 of Learner Onboarding.
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setShowResetModal(false)}
                disabled={resettingAccount}
              >
                Keep My Progress
              </button>
              <button
                type="button"
                className="btn btn--danger btn--sm"
                onClick={handleConfirmResetLearnerAccount}
                disabled={resettingAccount}
              >
                {resettingAccount ? 'Resetting...' : 'Yes, Delete Everything & Restart'}
              </button>
            </div>
          </div>
        </div>
      )}

      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: 'var(--surface-elevated, #1e293b)',
            color: 'var(--text-primary, #fff)',
            border: '1px solid var(--border-subtle, #334155)',
            boxShadow: 'var(--shadow-lg)',
            padding: '12px 18px',
            borderRadius: 'var(--r-md, 8px)',
            fontSize: '0.86rem',
            zIndex: 99,
          }}
        >
          {toastMessage}
        </div>
      )}

      {showLogoutToast && (
        <Toast
          message="Are you sure you want to log out?"
          confirmLabel="Yes, log out"
          onConfirm={handleSignOut}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </div>
  );
}
