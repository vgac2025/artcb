import { useState, useEffect } from 'react';
import { Language, Translations, getCurrentLanguage, getTranslation } from './translations';

export function useTranslation() {
  const [language, setLanguageState] = useState<Language>(getCurrentLanguage());

  useEffect(() => {
    const handleLanguageChange = () => {
      setLanguageState(getCurrentLanguage());
    };

    window.addEventListener('languagechange', handleLanguageChange);
    return () => window.removeEventListener('languagechange', handleLanguageChange);
  }, []);

  const t = (key: keyof Translations): string => {
    return getTranslation(language, key);
  };

  return { t, language };
}

