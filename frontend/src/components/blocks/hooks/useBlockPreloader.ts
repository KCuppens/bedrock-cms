import { useEffect } from 'react';
import { BlockRegistry } from '../BlockRegistry';

export const useBlockPreloader = (blockTypes: string[]): void => {
  useEffect(() => {
    const registry = BlockRegistry.getInstance();
    let idleId: number | null = null;
    let timeoutId: NodeJS.Timeout | null = null;

    const preloadCritical = (): void => {
      const criticalComponents = blockTypes
        .map(type => `${type.charAt(0).toUpperCase() + type.slice(1)}Block`)
        .filter(componentName => {
          const config = registry.getConfig(componentName);
          return config?.preload === true;
        });

      if (criticalComponents.length > 0) {
        registry.preloadComponents(criticalComponents);
      }
    };

    if ('requestIdleCallback' in window) {
      idleId = requestIdleCallback(preloadCritical);
    } else {
      timeoutId = setTimeout(preloadCritical, 100);
    }

    // Cleanup function
    return () => {
      if (idleId !== null && 'cancelIdleCallback' in window) {
        cancelIdleCallback(idleId);
      }
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [blockTypes]);
};