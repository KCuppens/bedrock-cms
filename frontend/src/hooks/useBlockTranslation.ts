import { useEffect, useMemo } from 'react';
import { useTranslation } from '@/contexts/TranslationContext';
import type { TranslationKey } from '@/types/translations';

interface BlockTranslationOptions {
  blockType: string;
  namespace?: string;
  keys?: Record<string, string>; // key -> defaultValue mapping
}

export const useBlockTranslation = (options: BlockTranslationOptions) => {
  const { t, registerKey } = useTranslation();
  const { blockType, namespace = 'blocks', keys = {} } = options;

  // Register block-specific keys on mount
  useEffect(() => {
    Object.entries(keys).forEach(([shortKey, defaultValue]) => {
      const fullKey = `${namespace}.${blockType}.${shortKey}`;
      registerKey({
        key: fullKey,
        defaultValue,
        description: `Used in ${blockType} block`,
        namespace
      });
    });
  }, [blockType, namespace, keys, registerKey]);

  // Create scoped translation function
  const blockT = useMemo(() => {
    return (shortKey: string, defaultValue?: string) => {
      const fullKey = `${namespace}.${blockType}.${shortKey}`;
      return t(fullKey, defaultValue || keys[shortKey]);
    };
  }, [namespace, blockType, t, keys]);

  return { t: blockT, globalT: t };
};