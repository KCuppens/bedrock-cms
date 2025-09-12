import { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';
import { parse } from '@babel/parser';
// @ts-ignore
import traverse from '@babel/traverse';

interface ExtractedKey {
  key: string;
  defaultValue: string;
  namespace: string;
  component: string;
  file: string;
  line: number;
}

export function translationExtractionPlugin(): Plugin {
  const extractedKeys = new Map<string, ExtractedKey>();

  // Track which components use which keys
  const componentKeys = new Map<string, Set<string>>();

  return {
    name: 'vite-plugin-translation-extraction',

    transform(code: string, id: string) {
      if (id.includes('node_modules') || !id.match(/\.(tsx?|jsx?)$/)) {
        return null;
      }

      try {
        const ast = parse(code, {
          sourceType: 'module',
          plugins: ['typescript', 'jsx']
        });

        const fileName = path.relative(process.cwd(), id);
        const componentName = path.basename(id, path.extname(id));

        // Use traverse.default if it exists, otherwise use traverse directly
        const traverseFn = (traverse as any).default || traverse;

        traverseFn(ast, {
          CallExpression(path: any) {
            const { node } = path;

            // Detect useBlockTranslation calls
            if (node.callee.type === 'Identifier' && node.callee.name === 'useBlockTranslation') {
              const [optionsArg] = node.arguments;

              if (optionsArg?.type === 'ObjectExpression') {
                let blockType = '';
                const keys: Record<string, string> = {};

                optionsArg.properties.forEach((prop: any) => {
                  if (prop.type === 'ObjectProperty') {
                    const propName = prop.key.name || prop.key.value;

                    if (propName === 'blockType' && prop.value.type === 'StringLiteral') {
                      blockType = prop.value.value;
                    }

                    if (propName === 'keys' && prop.value.type === 'ObjectExpression') {
                      prop.value.properties.forEach((keyProp: any) => {
                        if (keyProp.type === 'ObjectProperty' && keyProp.value.type === 'StringLiteral') {
                          const keyName = keyProp.key.name || keyProp.key.value;
                          keys[keyName] = keyProp.value.value;
                        }
                      });
                    }
                  }
                });

                // Register block translation keys
                if (blockType) {
                  Object.entries(keys).forEach(([shortKey, defaultValue]) => {
                    const fullKey = `blocks.${blockType}.${shortKey}`;
                    extractedKeys.set(fullKey, {
                      key: fullKey,
                      defaultValue,
                      namespace: 'blocks',
                      component: componentName,
                      file: fileName,
                      line: node.loc?.start.line || 0
                    });
                  });
                }
              }
            }

            // Detect direct t() calls
            if (node.callee.type === 'Identifier' && node.callee.name === 't') {
              const [keyArg, defaultArg] = node.arguments;

              if (keyArg?.type === 'StringLiteral') {
                const key = keyArg.value;
                const defaultValue = defaultArg?.type === 'StringLiteral'
                  ? defaultArg.value
                  : key;

                const namespace = key.split('.')[0] || 'general';

                extractedKeys.set(key, {
                  key,
                  defaultValue,
                  namespace,
                  component: componentName,
                  file: fileName,
                  line: node.loc?.start.line || 0
                });
              }
            }
          }
        });
      } catch (error: any) {
        // Only log actual parse errors, not traverse errors
        if (!error.message?.includes('traverse is not a function')) {
          console.warn(`Failed to parse ${id}:`, error.message);
        }
      }

      return null;
    },

    async buildEnd() {
      // Convert to format expected by backend
      const keysForBackend = Array.from(extractedKeys.values()).map(item => ({
        key: item.key,
        defaultValue: item.defaultValue,
        description: `Used in ${item.component} (${item.file}:${item.line})`,
        namespace: item.namespace
      }));

      // Write to file for sync script
      const outputPath = path.resolve(process.cwd(), 'extracted-translations.json');
      fs.writeFileSync(outputPath, JSON.stringify({
        timestamp: new Date().toISOString(),
        keys: keysForBackend,
        stats: {
          total: keysForBackend.length,
          byNamespace: keysForBackend.reduce((acc, k) => {
            acc[k.namespace] = (acc[k.namespace] || 0) + 1;
            return acc;
          }, {} as Record<string, number>),
          components: Array.from(new Set(Array.from(extractedKeys.values()).map(k => k.component)))
        }
      }, null, 2));

      console.log(`\n📝 Extracted ${keysForBackend.length} translation keys`);
      console.log(`   Saved to: ${outputPath}\n`);
    }
  };
}
