import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import enCommon from '../locales/en/common.json';
import caCommon from '../locales/ca/common.json';
import esCommon from '../locales/es/common.json';

export const defaultNS = 'common';
export const resources = {
  en: {
    common: enCommon,
  },
  ca: {
    common: caCommon,
  },
  es: {
    common: esCommon,
  },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    defaultNS,
    resources,
    lng: 'en', // default language
    fallbackLng: 'en',
    
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    
    react: {
      useSuspense: false, // We don't want to use Suspense
    },
  });

export default i18n;