import { ComponentType } from 'react';
import type { BlockComponentProps, BlockConfig } from './types';

const blockComponents = import.meta.glob('./blocks/*/index.tsx', {
  eager: false
});

const blockConfigs = import.meta.glob('./blocks/*/config.ts', {
  eager: true
});

export class BlockRegistry {
  private static instance: BlockRegistry;
  private components = new Map<string, () => Promise<any>>();
  private configs = new Map<string, BlockConfig>();
  private loadingPromises = new Map<string, Promise<ComponentType<BlockComponentProps>>>();
  private loadedComponents = new Map<string, ComponentType<BlockComponentProps>>();

  private constructor() {
    this.initializeRegistry();
  }

  static getInstance(): BlockRegistry {
    if (!BlockRegistry.instance) {
      BlockRegistry.instance = new BlockRegistry();
    }
    return BlockRegistry.instance;
  }

  private initializeRegistry(): void {
    Object.entries(blockComponents).forEach(([path, importFn]) => {
      const componentName = this.extractComponentName(path);
      if (componentName) {
        this.components.set(componentName, importFn as () => Promise<any>);
      }
    });

    Object.entries(blockConfigs).forEach(([path, configModule]) => {
      const componentName = this.extractComponentName(path);
      if (componentName) {
        const config = (configModule as any).default || (configModule as any).config;
        if (config) {
          this.configs.set(componentName, config);
        }
      }
    });

    console.log(`[BlockRegistry] Auto-discovered ${this.components.size} block components:`, Array.from(this.components.keys()));
    console.log(`[BlockRegistry] Auto-discovered ${this.configs.size} block configs:`, Array.from(this.configs.keys()));
  }

  private extractComponentName(path: string): string | null {
    const match = path.match(/\/blocks\/([^/]+)\//);
    return match ? match[1] : null;
  }

  async getComponent(componentName: string): Promise<ComponentType<BlockComponentProps> | null> {
    console.log(`[BlockRegistry] Getting component: ${componentName}`);

    // First try exact match
    if (this.components.has(componentName)) {
      return this.loadComponent(componentName);
    }

    // Try case-insensitive match
    const lowercaseName = componentName.toLowerCase();
    const matchingKey = Array.from(this.components.keys()).find(key => key.toLowerCase() === lowercaseName);

    if (matchingKey) {
      console.log(`[BlockRegistry] Found case-insensitive match: ${componentName} -> ${matchingKey}`);
      return this.loadComponent(matchingKey);
    }

    // Try common camelCase to lowercase transformations
    const transformedNames = [
      componentName.replace(/([A-Z])/g, (match, p1) => p1.toLowerCase()), // richText -> richtext
      componentName.replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase(), // richText -> rich_text
    ];

    for (const transformedName of transformedNames) {
      if (this.components.has(transformedName)) {
        console.log(`[BlockRegistry] Found transformed match: ${componentName} -> ${transformedName}`);
        return this.loadComponent(transformedName);
      }
    }

    console.warn(`[BlockRegistry] Component ${componentName} not found in registry`);
    console.log('[BlockRegistry] Available components:', Array.from(this.components.keys()));
    return null;
  }

  private async loadComponent(componentName: string): Promise<ComponentType<BlockComponentProps> | null> {
    // Return cached component if already loaded
    if (this.loadedComponents.has(componentName)) {
      console.log(`[BlockRegistry] Returning cached component: ${componentName}`);
      return this.loadedComponents.get(componentName)!;
    }

    // Return existing loading promise if component is currently being loaded
    if (this.loadingPromises.has(componentName)) {
      console.log(`[BlockRegistry] Component ${componentName} is already loading`);
      return this.loadingPromises.get(componentName)!;
    }

    console.log(`[BlockRegistry] Loading component: ${componentName}`);
    const loadingPromise = this.components.get(componentName)!()
      .then((module: any) => {
        console.log(`[BlockRegistry] Loaded module for ${componentName}:`, module);
        const Component = module.default || module;
        // Cache the loaded component and clean up the loading promise
        this.loadedComponents.set(componentName, Component);
        this.loadingPromises.delete(componentName);
        console.log(`[BlockRegistry] Successfully loaded and cached: ${componentName}`);
        return Component;
      })
      .catch((error: Error) => {
        console.error(`[BlockRegistry] Failed to load block component ${componentName}:`, error);
        this.loadingPromises.delete(componentName);
        throw error;
      });

    this.loadingPromises.set(componentName, loadingPromise);
    return loadingPromise;
  }

  getConfig(componentName: string): BlockConfig | null {
    return this.configs.get(componentName) || null;
  }

  getAllComponentNames(): string[] {
    return Array.from(this.components.keys());
  }

  async preloadComponents(componentNames: string[]): Promise<void> {
    const promises = componentNames.map(name => this.getComponent(name));
    await Promise.allSettled(promises);
  }
}
