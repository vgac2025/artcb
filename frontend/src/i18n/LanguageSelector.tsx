import { useState, useEffect } from 'react';
import { Language, getCurrentLanguage, setLanguage } from './translations';

const languages: { code: Language; name: string; flag: string }[] = [
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt', name: 'Português', flag: '🇵🇹' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
];

export function LanguageSelector() {
  const [currentLang, setCurrentLang] = useState<Language>(getCurrentLanguage());
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleLanguageChange = () => {
      setCurrentLang(getCurrentLanguage());
    };

    window.addEventListener('languagechange', handleLanguageChange);
    return () => window.removeEventListener('languagechange', handleLanguageChange);
  }, []);

  const handleLanguageChange = (lang: Language) => {
    setLanguage(lang);
    setCurrentLang(lang);
    setIsOpen(false);
    window.location.reload(); // Reload to apply translations
  };

  const currentLanguage = languages.find(l => l.code === currentLang) || languages[1];

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'var(--terminal-bg)',
          border: '1px solid var(--border-dark)',
          borderRadius: '6px',
          color: 'var(--terminal-text)',
          cursor: 'pointer',
          fontSize: '14px',
          fontFamily: 'var(--font-body)',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--terminal-accent)';
          e.currentTarget.style.background = 'var(--border-dark)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--border-dark)';
          e.currentTarget.style.background = 'var(--terminal-bg)';
        }}
      >
        <span style={{ fontSize: '18px' }}>{currentLanguage.flag}</span>
        <span>{currentLanguage.code.toUpperCase()}</span>
        <span style={{ fontSize: '10px' }}>▼</span>
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: '4px',
            background: 'var(--terminal-bg)',
            border: '1px solid var(--border-dark)',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            minWidth: '180px',
          }}
        >
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '10px 16px',
                background: lang.code === currentLang ? 'var(--border-dark)' : 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--border-dark)',
                color: 'var(--terminal-text)',
                cursor: 'pointer',
                fontSize: '14px',
                fontFamily: 'var(--font-body)',
                textAlign: 'left',
                transition: 'background 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (lang.code !== currentLang) {
                  e.currentTarget.style.background = 'var(--border-dark)';
                }
              }}
              onMouseLeave={(e) => {
                if (lang.code !== currentLang) {
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <span style={{ fontSize: '20px' }}>{lang.flag}</span>
              <span>{lang.name}</span>
              {lang.code === currentLang && (
                <span style={{ marginLeft: 'auto', color: 'var(--terminal-success)' }}>✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

