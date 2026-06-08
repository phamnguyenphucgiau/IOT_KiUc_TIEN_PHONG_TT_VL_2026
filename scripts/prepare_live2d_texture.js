#!/usr/bin/env node
/**
 * Integrate converted anime face into Live2D model
 * This script prepares the anime face for Live2D texture replacement
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = __dirname.includes('scripts') 
  ? path.dirname(__dirname) 
  : __dirname;

const PROCESSED_DIR = path.join(PROJECT_ROOT, 'processed_faces');
const LIVE2D_DIR = path.join(PROJECT_ROOT, 'haru_greeter_pro_jp', 'haru_greeter_pro_jp', 'runtime');
const TEXTURE_DIR = path.join(LIVE2D_DIR, 'haru_greeter_t05.2048');
const OUTPUT_DIR = path.join(PROJECT_ROOT, 'anime_face_textures');

// Ensure directories exist
[PROCESSED_DIR, OUTPUT_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

function convertAndPrepareTexture() {
  try {
    console.log('=' .repeat(60));
    console.log('ANIME FACE TO LIVE2D TEXTURE CONVERTER');
    console.log('=' .repeat(60));

    const animeSource = path.join(PROCESSED_DIR, 'anh1_face_anime_upscaled.jpg');
    
    if (!fs.existsSync(animeSource)) {
      console.error('[ERROR] Anime face file not found:', animeSource);
      console.error('[!] Run face_to_anime.py first!');
      return false;
    }

    console.log('[*] Input anime face:', animeSource);
    
    // Copy to output directory (ready for Live2D)
    const copiedPath = path.join(OUTPUT_DIR, 'anh1_face_anime_live2d.jpg');
    fs.copyFileSync(animeSource, copiedPath);
    console.log('[+] Copied to output directory:', copiedPath);

    // Create metadata
    const metadata = {
      originalImage: 'anh1.jpg',
      processedDate: new Date().toISOString(),
      textures: {
        live2d: 'anh1_face_anime_live2d.jpg'
      },
      live2dIntegration: {
        targetModel: 'haru_greeter_t05.model3.json',
        textureDirectory: TEXTURE_DIR,
        instructions: [
          '1. Backup existing texture in ' + TEXTURE_DIR,
          '2. Replace texture with: anh1_face_anime_live2d.jpg',
          '3. Update model3.json to reference new texture',
          '4. Reload viewer or restart server'
        ]
      }
    };

    const metadataPath = path.join(OUTPUT_DIR, 'README.json');
    fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
    console.log('[+] Metadata saved:', metadataPath);

    console.log('\n' + '=' .repeat(60));
    console.log('CONVERSION COMPLETE!');
    console.log('=' .repeat(60));
    console.log('\nGenerated texture in:', OUTPUT_DIR);
    console.log('\nTexture file:');
    
    const file = 'anh1_face_anime_live2d.jpg';
    const fullPath = path.join(OUTPUT_DIR, file);
    if (fs.existsSync(fullPath)) {
      const size = fs.statSync(fullPath).size;
      console.log(`  - ${file} (${size} bytes)`);
    }

    console.log('\nNext steps:');
    console.log('1. Navigate to Live2D texture directory:');
    console.log('   ' + TEXTURE_DIR);
    console.log('\n2. Backup the original texture file');
    console.log('\n3. Copy anime face texture:');
    console.log('   From: ' + fullPath);
    console.log('   To: ' + TEXTURE_DIR);
    console.log('\n4. Reload the viewer or restart the server');
    console.log('\nFor detailed info, see:', metadataPath);
    
    return true;

  } catch (error) {
    console.error('[ERROR]', error.message);
    return false;
  }
}

// Main
const success = convertAndPrepareTexture();
process.exit(success ? 0 : 1);
