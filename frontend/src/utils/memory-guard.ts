// Memory guard to prevent out-of-memory crashes
export class MemoryGuard {
  private static instance: MemoryGuard | null = null;
  private checkInterval: NodeJS.Timeout | null = null;
  private warningThreshold = 0.85; // 85% memory usage
  private criticalThreshold = 0.95; // 95% memory usage
  private lastCleanup = Date.now();
  
  private constructor() {
    this.startMonitoring();
  }
  
  static getInstance(): MemoryGuard {
    if (!MemoryGuard.instance) {
      MemoryGuard.instance = new MemoryGuard();
    }
    return MemoryGuard.instance;
  }
  
  private startMonitoring(): void {
    // Only monitor in browsers that support memory API
    if (!(performance as any).memory) return;
    
    this.checkInterval = setInterval(() => {
      this.checkMemory();
    }, 10000); // Check every 10 seconds
  }
  
  private checkMemory(): void {
    const memory = (performance as any).memory;
    if (!memory) return;
    
    const usedMemory = memory.usedJSHeapSize;
    const totalMemory = memory.jsHeapSizeLimit;
    const usage = usedMemory / totalMemory;
    
    if (usage > this.criticalThreshold) {
      console.error(`CRITICAL: Memory usage at ${(usage * 100).toFixed(1)}%`);
      // Emit memory pressure event for app-wide cleanup
      window.dispatchEvent(new CustomEvent('memory-pressure', { detail: { level: 'critical', usage } }));
      this.emergencyCleanup();
    } else if (usage > this.warningThreshold) {
      console.warn(`WARNING: High memory usage at ${(usage * 100).toFixed(1)}%`);
      // Emit memory pressure event for app-wide cleanup
      window.dispatchEvent(new CustomEvent('memory-pressure', { detail: { level: 'warning', usage } }));
      this.performCleanup();
    }
  }
  
  private performCleanup(): void {
    const now = Date.now();
    // Only cleanup once per minute
    if (now - this.lastCleanup < 60000) return;
    
    this.lastCleanup = now;
    
    // Clear caches
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
    }
    
    // Clear session storage of old data
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key && key.startsWith('temp_') || key?.startsWith('cache_')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => sessionStorage.removeItem(key));
    } catch (e) {
      console.error('Failed to clear session storage:', e);
    }
    
    // Trigger garbage collection if available
    if ((window as any).gc) {
      (window as any).gc();
    }
    
    console.log('Memory cleanup performed');
  }
  
  private emergencyCleanup(): void {
    console.error('Emergency memory cleanup initiated');
    
    // Aggressive cleanup
    this.performCleanup();
    
    // Clear all non-essential data
    sessionStorage.clear();
    
    // Reload page if still critical after cleanup
    setTimeout(() => {
      const memory = (performance as any).memory;
      if (memory) {
        const usage = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
        if (usage > this.criticalThreshold) {
          console.error('Memory still critical, reloading page...');
          window.location.reload();
        }
      }
    }, 2000);
  }
  
  destroy(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    MemoryGuard.instance = null;
  }
}

// Initialize memory guard
export const initMemoryGuard = (): MemoryGuard => {
  return MemoryGuard.getInstance();
};