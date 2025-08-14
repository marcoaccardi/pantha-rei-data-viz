import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSelector: React.FC = () => {
  const { i18n } = useTranslation();

  const languages = [
    { 
      code: 'en', 
      name: 'English', 
      initial: 'EN',
      ariaLabel: 'Switch to English'
    },
    { 
      code: 'ca', 
      name: 'Català', 
      initial: 'CA',
      ariaLabel: 'Canviar a Català'
    },
    { 
      code: 'es', 
      name: 'Español', 
      initial: 'ES',
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
      top: '50%',
      transform: 'translateY(-50%)',
      left: '20px',
      zIndex: 1001,
      display: 'flex',
      flexDirection: 'column', // Vertical layout
      gap: '10px'
    }}>
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => changeLanguage(lang.code)}
          aria-label={lang.ariaLabel}
          title={lang.name}
          style={{
            backgroundColor: currentLanguage === lang.code 
              ? 'rgba(156, 163, 175, 0.3)' 
              : 'transparent',
            border: currentLanguage === lang.code
              ? '1px solid #9ca3af'
              : '1px solid rgba(156, 163, 175, 0.6)',
            borderRadius: '50%',
            padding: '0',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: '500',
            color: '#f9fafb',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            width: '36px',
            height: '36px',
            backdropFilter: 'blur(10px)'
          }}
          onMouseOver={(e) => {
            if (currentLanguage !== lang.code) {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
              e.currentTarget.style.borderColor = 'rgba(229, 231, 235, 0.8)';
            }
          }}
          onMouseOut={(e) => {
            if (currentLanguage !== lang.code) {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.6)';
            }
          }}
        >
          {lang.initial}
        </button>
      ))}
    </div>
  );
};

export default LanguageSelector;