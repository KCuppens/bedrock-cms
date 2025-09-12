#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const MANIFEST_PATH = path.join(process.cwd(), 'extracted-translations.json');
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const API_TOKEN = process.env.TRANSLATION_SYNC_TOKEN;

async function syncTranslations() {
  console.log('🔄 Starting translation sync...\n');

  // Read manifest
  if (!fs.existsSync(MANIFEST_PATH)) {
    console.error('❌ No translation manifest found. Run build first.');
    process.exit(1);
  }

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8'));
  console.log(`📊 Found ${manifest.stats.total} translation keys\n`);
  console.log('   By namespace:');
  Object.entries(manifest.stats.byNamespace).forEach(([ns, count]) => {
    console.log(`     - ${ns}: ${count} keys`);
  });
  console.log('');

  // Send to backend
  try {
    const headers = {
      'Content-Type': 'application/json'
    };

    if (API_TOKEN) {
      headers['Authorization'] = `Token ${API_TOKEN}`;
    }

    // Use fetch (Node 18+) or node-fetch
    const fetch = globalThis.fetch || require('node-fetch');

    const response = await fetch(`${API_URL}/i18n/ui-messages/sync-keys/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        keys: manifest.keys,
        source: 'build'
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();

    console.log('✅ Sync complete:');
    console.log(`   - Created: ${result.created.length} new keys`);
    console.log(`   - Updated: ${result.updated.length} existing keys`);
    console.log(`   - Total processed: ${result.total_processed}`);

    if (result.created.length > 0) {
      console.log('\n📝 New keys created:');
      result.created.forEach(key => console.log(`   - ${key}`));
    }

    if (result.errors && result.errors.length > 0) {
      console.log('\n⚠️ Errors:');
      result.errors.forEach(err => console.log(`   - ${err.key}: ${err.error}`));
    }
  } catch (error) {
    console.error('❌ Sync failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  syncTranslations().catch(error => {
    console.error('Unexpected error:', error);
    process.exit(1);
  });
}

module.exports = { syncTranslations };