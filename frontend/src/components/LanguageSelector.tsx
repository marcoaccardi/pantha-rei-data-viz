import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSelector: React.FC = () => {
  const { i18n } = useTranslation();

  const languages = [
    { 
      code: 'en', 
      name: 'English', 
      flag: '🇬🇧',
      ariaLabel: 'Switch to English'
    },
    { 
      code: 'ca', 
      name: 'Català', 
      flag: '🏴󠁥󠁳󠁣󠁴󠁿',
      ariaLabel: 'Canviar a Català'
    },
    { 
      code: 'es', 
      name: 'Español', 
      flag: '🇪🇸',
      ariaLabel: 'Cambiar a Español'
    }
  ];

  const changeLanguage = (languageCode: string) => {
    i18n.changeLanguage(languageCode);
  };

  const currentLanguage = i18n.language;

  return (
    <div style={{
      position: 'absolute',
      top: '420px', // Position below the control panel
      left: '20px',
      zIndex: 1001,
      display: 'flex',
      flexDirection: 'column', // Vertical layout
      gap: '6px',
      backgroundColor: 'rgba(0, 0, 0, 0.85)',
      padding: '8px',
      borderRadius: '8px',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(156, 163, 175, 0.4)'
    }}>
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => changeLanguage(lang.code)}
          aria-label={lang.ariaLabel}
          title={lang.name}
          style={{
            backgroundColor: currentLanguage === lang.code 
              ? 'rgba(59, 130, 246, 0.3)' 
              : 'transparent',
            border: currentLanguage === lang.code
              ? '1px solid #3b82f6'
              : '1px solid rgba(156, 163, 175, 0.3)',
            borderRadius: '6px',
            padding: '6px 10px',
            cursor: 'pointer',
            fontSize: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            minWidth: '40px',
            height: '32px'
          }}
          onMouseOver={(e) => {
            if (currentLanguage !== lang.code) {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.6)';
            }
          }}
          onMouseOut={(e) => {
            if (currentLanguage !== lang.code) {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.3)';
            }
          }}
        >
          <span role="img" aria-label={`${lang.name} flag`}>
            {lang.flag}
          </span>
        </button>
      ))}
    </div>
  );
};

export default LanguageSelector;