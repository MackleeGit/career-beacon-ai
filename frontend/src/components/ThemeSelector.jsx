// src/components/ThemeSelector.jsx
import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { Sun, Moon, Monitor } from './Icons';

const OPTIONS = [
  { id: 'light', label: 'Light', Icon: Sun },
  { id: 'dark', label: 'Dark', Icon: Moon },
  { id: 'system', label: 'System', Icon: Monitor },
];

export default function ThemeSelector({ showLabels = false, size = 'sm' }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="group"
      aria-label="Theme selection"
      className={`theme-selector ${size === 'md' ? 'theme-selector--md' : ''}`}
    >
      {OPTIONS.map(({ id, label, Icon }) => {
        const isActive = theme === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => setTheme(id)}
            aria-pressed={isActive}
            aria-label={`${label} theme`}
            title={`${label} theme`}
            className={`theme-selector__btn ${isActive ? 'is-active' : ''}`}
          >
            <Icon size={size === 'md' ? 16 : 14} />
            {showLabels && <span>{label}</span>}
          </button>
        );
      })}
    </div>
  );
}

