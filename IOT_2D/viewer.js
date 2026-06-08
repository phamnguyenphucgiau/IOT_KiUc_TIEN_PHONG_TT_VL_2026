const MODEL_PATH_ORIGINAL = "./haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05.model3.json";
const MODEL_PATH_AOCONGSO = "./haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05_aocongso.model3.json";
const AUDIO_PATH = "./voice.mp3";
const TOTAL_MOTIONS = 27;
const MOTION_GROUP = "";
const FORCE_PRIORITY = 3;
const MOUTH_PARAMETER_ID = "ParamMouthOpenY";

const appRoot = document.getElementById("app");
const statusEl = document.getElementById("status");
const playMotionButton = document.getElementById("playMotion");
const playVoiceButton = document.getElementById("playVoice");
const resetViewButton = document.getElementById("resetView");
const switchOutfitButton = document.getElementById("switchOutfit");
const switchHairstyleButton = document.getElementById("switchHairstyle");
const switchEyesButton = document.getElementById("switchEyes");

const app = new PIXI.Application({
  resizeTo: window,
  autoDensity: true,
  antialias: true,
  backgroundAlpha: 0
});

appRoot.appendChild(app.view);

let model;
let currentMotion = 0;
let dragging = false;
let dragOffset = { x: 0, y: 0 };
let audioElement;
let audioContext;
let audioAnalyser;
let audioData;
let audioSourceNode;
let lipsyncActive = false;
let mouthValue = 0;
let pointerTarget = { x: 0, y: 0 };
let pointerSmooth = { x: 0, y: 0 };
let motionClock = 0;
let baseTransform = {
  x: 0,
  y: 0,
  scale: 1
};
let targetTransform = {
  x: 0,
  y: 0,
  scale: 1
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function updateStatus(text) {
  statusEl.textContent = text;
}

function fitModelToScreen() {
  if (!model) {
    return;
  }

  model.scale.set(1);
  model.anchor.set(0.5, 0.5);

  const bounds = model.getLocalBounds();
  const leftPanel = document.querySelector(".left");
  const isCollapsed = leftPanel && leftPanel.classList.contains("collapsed");

  const maxWidth = window.innerWidth * (isCollapsed ? 0.85 : 0.58);
  const maxHeight = window.innerHeight * 0.95;
  const scale = Math.min(maxWidth / bounds.width, maxHeight / bounds.height);

  targetTransform.scale = scale;
  targetTransform.x = window.innerWidth * (isCollapsed ? 0.5 : 0.6);
  targetTransform.y = window.innerHeight * 0.58;

  if (baseTransform.x === 0 && baseTransform.y === 0) {
    baseTransform.x = targetTransform.x;
    baseTransform.y = targetTransform.y;
    baseTransform.scale = targetTransform.scale;
  }

  model.scale.set(baseTransform.scale);
  model.position.set(baseTransform.x, baseTransform.y);
}

function setParameter(id, value, weight = 0.2) {
  const coreModel = model?.internalModel?.coreModel;

  if (!coreModel) {
    return;
  }

  if (typeof coreModel.addParameterValueById === "function") {
    coreModel.addParameterValueById(id, value, weight);
    return;
  }

  if (typeof coreModel.setParameterValueById === "function") {
    coreModel.setParameterValueById(id, value);
  }
}

async function playMotion(index) {
  if (!model?.motion) {
    return;
  }

  currentMotion = ((index % TOTAL_MOTIONS) + TOTAL_MOTIONS) % TOTAL_MOTIONS;

  try {
    const started = await model.motion(MOTION_GROUP, currentMotion, FORCE_PRIORITY);
    updateStatus(started ? `Dang chay animation #${currentMotion}` : `Animation #${currentMotion} chua chay duoc`);
  } catch (error) {
    console.error("Motion error:", error);
    updateStatus(`Loi khi chay animation #${currentMotion}`);
  }
}

function setMouthOpen(value) {
  const coreModel = model?.internalModel?.coreModel;

  if (!coreModel) {
    return;
  }

  const normalized = clamp(value, 0, 1);
  mouthValue = normalized;

  if (typeof coreModel.setParameterValueById === "function") {
    coreModel.setParameterValueById(MOUTH_PARAMETER_ID, normalized);
  }

  if (typeof coreModel.addParameterValueById === "function") {
    coreModel.addParameterValueById(MOUTH_PARAMETER_ID, normalized, 1);
  }
}

function bindModelPointer() {
  model.eventMode = "static";
  model.cursor = "grab";

  model.on("pointerdown", (event) => {
    dragging = true;
    const point = event.data.global;
    model.cursor = "grabbing";
    dragOffset.x = point.x - model.x;
    dragOffset.y = point.y - model.y;
  });

  model.on("pointerup", () => {
    dragging = false;
    model.cursor = "grab";
  });

  model.on("pointerupoutside", () => {
    dragging = false;
    model.cursor = "grab";
  });

  model.on("pointermove", (event) => {
    const point = event.data.global;

    if (dragging) {
      model.position.set(point.x - dragOffset.x, point.y - dragOffset.y);
      baseTransform.x = model.x;
      baseTransform.y = model.y;
      targetTransform.x = model.x;
      targetTransform.y = model.y;
      return;
    }

    pointerTarget.x = clamp((point.x / window.innerWidth - 0.5) * 2, -1, 1);
    pointerTarget.y = clamp((point.y / window.innerHeight - 0.5) * 2, -1, 1);
  });
}

function setupStagePointerTracking() {
  app.stage.eventMode = "static";
  app.stage.hitArea = app.screen;
  app.stage.on("pointermove", (event) => {
    const point = event.global;
    pointerTarget.x = clamp((point.x / window.innerWidth - 0.5) * 2, -1, 1);
    pointerTarget.y = clamp((point.y / window.innerHeight - 0.5) * 2, -1, 1);
  });
  app.stage.on("pointerleave", () => {
    pointerTarget.x = 0;
    pointerTarget.y = 0;
  });
}

function setupAudio() {
  audioElement = new Audio(AUDIO_PATH);
  audioElement.crossOrigin = "anonymous";

  audioElement.addEventListener("play", async () => {
    try {
      audioContext ??= new (window.AudioContext || window.webkitAudioContext)();

      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      if (!audioSourceNode) {
        audioSourceNode = audioContext.createMediaElementSource(audioElement);
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 512;
        audioData = new Uint8Array(audioAnalyser.frequencyBinCount);
        audioSourceNode.connect(audioAnalyser);
        audioAnalyser.connect(audioContext.destination);
      }

      lipsyncActive = true;
      updateStatus("Dang phat voice va lipsync...");
    } catch (error) {
      console.error("Audio setup error:", error);
      updateStatus("Khong the khoi tao audio context");
    }
  });

  audioElement.addEventListener("pause", () => {
    lipsyncActive = false;
  });

  audioElement.addEventListener("ended", () => {
    lipsyncActive = false;
    updateStatus(`Dang nghi o animation #${currentMotion}`);
  });
}

playVoiceButton.addEventListener("click", async () => {
  try {
    audioElement.currentTime = 0;
    await audioElement.play();
  } catch (error) {
    console.error("Audio play error:", error);
    updateStatus("Khong phat duoc voice");
  }
});

resetViewButton.addEventListener("click", () => {
  pointerTarget.x = 0;
  pointerTarget.y = 0;
  pointerSmooth.x = 0;
  pointerSmooth.y = 0;
  fitModelToScreen();
  updateStatus(`Da reset vi tri. Animation hien tai #${currentMotion}`);
});

app.ticker.add(() => {
  if (!model) {
    return;
  }

  motionClock += app.ticker.deltaMS * 0.001;
  pointerSmooth.x += (pointerTarget.x - pointerSmooth.x) * 0.08;
  pointerSmooth.y += (pointerTarget.y - pointerSmooth.y) * 0.08;

  // Smoothly interpolate position and scale towards target values
  baseTransform.x += (targetTransform.x - baseTransform.x) * 0.1;
  baseTransform.y += (targetTransform.y - baseTransform.y) * 0.1;
  baseTransform.scale += (targetTransform.scale - baseTransform.scale) * 0.1;

  model.scale.set(baseTransform.scale);

  const headX = pointerSmooth.x * 8;
  const headY = pointerSmooth.y * 5;
  const bodyX = pointerSmooth.x * 2.2;
  const eyeX = pointerSmooth.x * 0.38;
  const eyeY = pointerSmooth.y * 0.24;
  const idleBreath = Math.sin(motionClock * 1.6) * 0.08;

  setParameter("ParamAngleX", headX, 0.25);
  setParameter("ParamAngleY", headY, 0.25);
  setParameter("ParamBodyAngleX", bodyX, 0.18);
  setParameter("ParamEyeBallX", eyeX, 0.24);
  setParameter("ParamEyeBallY", eyeY, 0.24);
  setParameter("ParamBreath", idleBreath, 0.2);

  model.position.set(
    baseTransform.x + pointerSmooth.x * 12,
    baseTransform.y + pointerSmooth.y * 8
  );

  if (lipsyncActive && audioAnalyser && audioData) {
    audioAnalyser.getByteFrequencyData(audioData);
    const slice = audioData.slice(8, 64);
    const average = slice.reduce((sum, value) => sum + value, 0) / slice.length;
    const target = clamp((average - 12) / 72, 0, 1);
    mouthValue += (target - mouthValue) * 0.35;
    setMouthOpen(mouthValue);
  } else if (mouthValue > 0.001) {
    mouthValue *= 0.75;
    setMouthOpen(mouthValue);
  } else {
    mouthValue = 0;
    setMouthOpen(0);
  }
});


let currentModelPath = MODEL_PATH_ORIGINAL;
let activeTextureUrl = null;
let hairstyleState = "original";
let hairColorState = "black";
let eyesState = "original";

function getActiveClothingUrl() {
  const textureDir = "./haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05.2048/";
  if (currentModelPath === MODEL_PATH_AOCONGSO) {
    return activeTextureUrl || (textureDir + "texture_01_aocongso.png");
  } else {
    return textureDir + "texture_01_custom_alpha.png";
  }
}

// HSV / RGB conversion helpers for client-side ponytail pixel tinting
function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, v = max;
  const d = max - min;
  s = max === 0 ? 0 : d / max;
  if (max === min) {
    h = 0;
  } else {
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return [h * 180, s * 255, v * 255];
}

function hsvToRgb(h, s, v) {
  h /= 180; s /= 255; v /= 255;
  let r, g, b;
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  switch (i % 6) {
    case 0: r = v, g = t, b = p; break;
    case 1: r = q, g = v, b = p; break;
    case 2: r = p, g = v, b = t; break;
    case 3: r = p, g = q, b = v; break;
    case 4: r = t, g = p, b = v; break;
    case 5: r = v, g = p, b = q; break;
  }
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

function getChibiClothingTextureUrl(sourceUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0);

        // Bounding box for ponytail in texture_01: x=1682, y=1559, w=344, h=481
        const px = 1682;
        const py = 1559;
        const pw = 344;
        const ph = 481;

        if (px + pw <= canvas.width && py + ph <= canvas.height) {
          const imgData = ctx.getImageData(px, py, pw, ph);
          const data = imgData.data;

          for (let i = 0; i < data.length; i += 4) {
            const a = data[i + 3];
            if (a > 10) {
              const r = data[i];
              const g = data[i + 1];
              const b = data[i + 2];

              // Convert RGB to HSV
              const hsv = rgbToHsv(r, g, b);
              const h = hsv[0];
              const s = hsv[1];
              const v = hsv[2];

              let new_h, new_s, new_v;
              if (hairColorState === "brown") {
                new_h = 12;
                new_s = Math.max(0, Math.min(255, s * 1.5 + 40));
                new_v = Math.max(0, Math.min(255, v * 1.5 + 20));
              } else if (hairColorState === "lightbrown") {
                new_h = 15;
                new_s = Math.max(0, Math.min(255, s * 1.2 + 30));
                new_v = Math.max(0, Math.min(255, v * 2.2 + 50));
              } else if (hairColorState === "red") {
                new_h = 0;
                new_s = Math.max(0, Math.min(255, s * 2.0 + 80));
                new_v = Math.max(0, Math.min(255, v * 2.0 + 20));
              } else if (hairColorState === "blue") {
                new_h = 115;
                new_s = Math.max(0, Math.min(255, s * 1.8 + 60));
                new_v = Math.max(0, Math.min(255, v * 1.8 + 20));
              } else if (hairColorState === "smokywhite") {
                new_h = 105;
                new_s = Math.max(0, Math.min(255, s * 0.15 + 10));
                new_v = Math.max(0, Math.min(255, v * 2.3 + 90));
              } else { // black
                new_h = 105;
                new_s = s * 0.40;
                new_v = v * 0.33;
              }

              // Convert back to RGB
              const rgb = hsvToRgb(new_h, new_s, new_v);
              data[i] = rgb[0];
              data[i + 1] = rgb[1];
              data[i + 2] = rgb[2];
            }
          }
          ctx.putImageData(imgData, px, py);
        }
        resolve(canvas.toDataURL("image/png"));
      } catch (err) {
        console.error("Error in getChibiClothingTextureUrl canvas processing:", err);
        resolve(sourceUrl);
      }
    };
    img.onerror = (e) => {
      console.error("Failed to load clothing image for ponytail tinting:", sourceUrl, e);
      resolve(sourceUrl);
    };
    img.src = sourceUrl;
  });
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = (e) => reject(e);
    img.src = url;
  });
}

async function getChibiEyesTextureUrl(baseHairUrl) {
  try {
    console.log("[*] Generating chibi eyes texture on top of:", baseHairUrl);
    const baseImg = await loadImage(baseHairUrl);
    const canvas = document.createElement("canvas");
    canvas.width = baseImg.width;
    canvas.height = baseImg.height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(baseImg, 0, 0);

    const [p20, p19, p24, p25] = await Promise.all([
      loadImage("./extracted_body/part_20_chibi.png"),
      loadImage("./extracted_body/part_19_chibi.png"),
      loadImage("./extracted_body/part_24_chibi.png"),
      loadImage("./extracted_body/part_25_chibi.png")
    ]);

    // Clear destination rects on canvas:
    // part_20 (Left Sclera): x=1273, y=1260, w=125, h=98
    // part_19 (Right Sclera): x=1431, y=1260, w=125, h=98
    // part_24 (Left Iris): x=1526, y=1168, w=87, h=98
    // part_25 (Right Iris): x=1615, y=1165, w=87, h=98
    ctx.clearRect(1273, 1260, 125, 98);
    ctx.clearRect(1431, 1260, 125, 98);
    ctx.clearRect(1526, 1168, 87, 98);
    ctx.clearRect(1615, 1165, 87, 98);

    // Draw new parts
    ctx.drawImage(p20, 1273, 1260, 125, 98);
    ctx.drawImage(p19, 1431, 1260, 125, 98);
    ctx.drawImage(p24, 1526, 1168, 87, 98);
    ctx.drawImage(p25, 1615, 1165, 87, 98);

    return canvas.toDataURL("image/png");
  } catch (err) {
    console.error("Error in getChibiEyesTextureUrl:", err);
    return baseHairUrl;
  }
}

function clearGlobalPixiCaches() {
  console.log("[*] Clearing PIXI texture caches and loader resources...");
  // 1. Clean PIXI.utils.TextureCache
  if (PIXI.utils && PIXI.utils.TextureCache) {
    const keys = Object.keys(PIXI.utils.TextureCache);
    keys.forEach(key => {
      if (key.includes("haru_greeter") || key.includes("texture_00") || key.includes("texture_01") || key.includes("chibihair") || key.startsWith("data:image") || (activeTextureUrl && key.includes(activeTextureUrl))) {
        const tex = PIXI.utils.TextureCache[key];
        if (tex) {
          PIXI.Texture.removeFromCache(tex);
          if (tex.baseTexture) {
            PIXI.BaseTexture.removeFromCache(tex.baseTexture);
            if (!tex.baseTexture.destroyed) {
              try { tex.baseTexture.destroy(); } catch (e) {}
            }
          }
          if (!tex.destroyed) {
            try { tex.destroy(); } catch (e) {}
          }
        }
        delete PIXI.utils.TextureCache[key];
      }
    });
  }

  // 2. Clean PIXI.utils.BaseTextureCache
  if (PIXI.utils && PIXI.utils.BaseTextureCache) {
    const keys = Object.keys(PIXI.utils.BaseTextureCache);
    keys.forEach(key => {
      if (key.includes("haru_greeter") || key.includes("texture_00") || key.includes("texture_01") || key.includes("chibihair") || key.startsWith("data:image") || (activeTextureUrl && key.includes(activeTextureUrl))) {
        const baseTex = PIXI.utils.BaseTextureCache[key];
        if (baseTex) {
          PIXI.BaseTexture.removeFromCache(baseTex);
          if (!baseTex.destroyed) {
            try { baseTex.destroy(); } catch (e) {}
          }
        }
        delete PIXI.utils.BaseTextureCache[key];
      }
    });
  }

  // 3. Reset PIXI.Loader.shared to clear resource references and status
  if (PIXI.Loader && PIXI.Loader.shared) {
    try {
      PIXI.Loader.shared.reset();
      console.log("[*] PIXI.Loader.shared reset successfully.");
    } catch (e) {
      console.warn("Failed to reset PIXI.Loader.shared:", e);
    }
  }
}

async function loadModel(modelPath) {
  try {
    let prevPosition = null;
    let prevScale = null;

    if (model) {
      // Save current position and scale to prevent layout jumping
      prevPosition = { x: model.position.x, y: model.position.y };
      prevScale = { x: model.scale.x, y: model.scale.y };

      app.stage.removeChild(model);
      model.destroy();
      model = null;
    }

    // Now clear the caches to ensure a fresh, un-destroyed load
    clearGlobalPixiCaches();

    updateStatus("Dang tai model Live2D...");
    model = await PIXI.live2d.Live2DModel.from(modelPath, {
      idleMotionGroup: MOTION_GROUP
    });

    // Apply the active hairstyle and outfit textures cleanly
    const textureDir = "./haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05.2048/";
    let tex0, tex1;

    let baseHairUrl;
    if (hairstyleState === "chibi") {
      const hairFilename = hairColorState === "black" ? "texture_00_chibihair.png" : `texture_00_chibi1_${hairColorState}.png`;
      baseHairUrl = textureDir + hairFilename;
    } else if (hairstyleState === "chibi2") {
      const hairFilename = hairColorState === "black" ? "texture_00_chibihair2.png" : `texture_00_chibi2_${hairColorState}.png`;
      baseHairUrl = textureDir + hairFilename;
    } else {
      baseHairUrl = textureDir + "texture_00.png";
    }

    if (eyesState === "chibi" || eyesState === "monolid") {
      const chibiEyesUrl = await getChibiEyesTextureUrl(baseHairUrl);
      tex0 = PIXI.Texture.from(chibiEyesUrl);
    } else {
      tex0 = PIXI.Texture.from(baseHairUrl);
    }

    const activeClothingUrl = getActiveClothingUrl();
    if (hairstyleState === "chibi" || hairstyleState === "chibi2") {
      const chibiClothingTexUrl = await getChibiClothingTextureUrl(activeClothingUrl);
      tex1 = PIXI.Texture.from(chibiClothingTexUrl);
    } else {
      tex1 = PIXI.Texture.from(activeClothingUrl);
    }

    // Safe helper function to wait for a texture to be valid with a safety timeout
    const waitForTexture = (tex) => {
      return new Promise(resolve => {
        if (!tex || !tex.baseTexture) {
          resolve();
          return;
        }
        if (tex.baseTexture.valid) {
          resolve();
          return;
        }
        // Safety timeout (1000ms) to guarantee that it never hangs the loader
        const timeoutId = setTimeout(() => {
          console.warn("[*] Texture load timeout for:", tex.textureCacheIds);
          resolve();
        }, 1000);

        tex.baseTexture.once("loaded", () => {
          clearTimeout(timeoutId);
          resolve();
        });
        tex.baseTexture.once("error", () => {
          clearTimeout(timeoutId);
          resolve();
        });
      });
    };

    // Wait for both textures to load to prevent visual pop-in or blank rendering
    await Promise.all([
      waitForTexture(tex0),
      waitForTexture(tex1)
    ]);

    model.textures[0] = tex0;
    model.textures[1] = tex1;

    app.stage.addChild(model);

    // Restore previous layout parameters if they exist, otherwise perform auto-fit
    if (prevPosition && prevScale) {
      model.scale.set(prevScale.x, prevScale.y);
      model.position.set(prevPosition.x, prevPosition.y);
      model.anchor.set(0.5, 0.5);
      baseTransform.x = prevPosition.x;
      baseTransform.y = prevPosition.y;
      baseTransform.scale = prevScale.x;
      targetTransform.x = prevPosition.x;
      targetTransform.y = prevPosition.y;
      targetTransform.scale = prevScale.x;
    } else {
      fitModelToScreen();
    }

    bindModelPointer();

    // Toggle hair color picker visibility depending on style
    updateHairColorPanelVisibility();

    updateStatus("Da tai model. Nhan nut de doi animation hoac phat voice.");
    await playMotion(currentMotion);

    model.on("hit", (hitAreas) => {
      if (hitAreas.length) {
        playMotion(currentMotion + 1);
      }
    });
  } catch (error) {
    console.error(error);
    updateStatus("Khong tai duoc model. Hay mo bang localhost cua XAMPP.");
  }
}

async function init() {
  setupAudio();
  setupStagePointerTracking();
  
  // Set initial button label
  switchHairstyleButton.textContent = "Kiểu tóc: Gốc";
  
  await loadModel(currentModelPath);
}

playMotionButton.addEventListener("click", async () => {
  await playMotion(currentMotion + 1);
});

switchOutfitButton.addEventListener("click", async () => {
  if (currentModelPath === MODEL_PATH_ORIGINAL) {
    currentModelPath = MODEL_PATH_AOCONGSO;
    switchOutfitButton.textContent = "Ve trang phuc cu";
  } else {
    currentModelPath = MODEL_PATH_ORIGINAL;
    switchOutfitButton.textContent = "Doi trang phuc";
  }
  await loadModel(currentModelPath);
});

switchHairstyleButton.addEventListener("click", async () => {
  if (!model) {
    updateStatus("Model chưa sẵn sàng.");
    return;
  }

  try {
    if (hairstyleState === "original") {
      hairstyleState = "chibi";
      switchHairstyleButton.textContent = "Kiểu tóc: Kiểu 1";
      updateStatus("Đang đổi sang kiểu tóc 1...");
    } else if (hairstyleState === "chibi") {
      hairstyleState = "chibi2";
      switchHairstyleButton.textContent = "Kiểu tóc: Kiểu 2";
      updateStatus("Đang đổi sang kiểu tóc 2...");
    } else {
      hairstyleState = "original";
      switchHairstyleButton.textContent = "Kiểu tóc: Gốc";
      updateStatus("Đang khôi phục kiểu tóc gốc...");
    }

    // Reload the active model to force clean WebGL texture bindings instantly
    await loadModel(currentModelPath);

    if (hairstyleState === "chibi") {
      updateStatus("Đã đổi sang kiểu tóc Chibi 1!");
    } else if (hairstyleState === "chibi2") {
      updateStatus("Đã đổi sang kiểu tóc Chibi 2!");
    } else {
      updateStatus("Đã quay lại kiểu tóc gốc!");
    }
  } catch (err) {
    console.error("Hairstyle switch error:", err);
    updateStatus("Lỗi khi đổi kiểu tóc: " + err.message);
  }
});

switchEyesButton.addEventListener("click", async () => {
  if (!model) {
    updateStatus("Model chưa sẵn sàng.");
    return;
  }

  try {
    if (eyesState === "original") {
      eyesState = "chibi";
      switchEyesButton.textContent = "Mắt: Chibi";
      updateStatus("Đang đổi sang mắt Chibi...");
    } else {
      eyesState = "original";
      switchEyesButton.textContent = "Mắt: Gốc";
      updateStatus("Đang khôi phục mắt gốc...");
    }

    await loadModel(currentModelPath);

    if (eyesState === "chibi") {
      updateStatus("Đã đổi sang mắt Chibi thành công!");
    } else {
      updateStatus("Đã quay lại mắt gốc thành công!");
    }
  } catch (err) {
    console.error("Eyes switch error:", err);
    updateStatus("Lỗi khi đổi mắt: " + err.message);
  }
});

const uploadClothingInput = document.getElementById("uploadClothingInput");
const uploadClothingBtn = document.getElementById("uploadClothingBtn");
const API_BASE_URL = `http://${window.location.hostname}:8000`;

uploadClothingBtn.addEventListener("click", () => {
  uploadClothingInput.click();
});

uploadClothingInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    alert("Vui lòng tải lên một file ảnh!");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    updateStatus("Đang tải lên và xử lý ảnh áo công sở mới...");
    uploadClothingBtn.disabled = true;
    uploadClothingBtn.textContent = "Đang xử lý...";

    const response = await fetch(`${API_BASE_URL}/api/upload-clothing`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Không thể xử lý ảnh.");
    }

    const data = await response.json();
    activeTextureUrl = `${API_BASE_URL}${data.texture_url}`;
    console.log("[*] Custom texture loaded:", activeTextureUrl);

    // Switch to the costume model path and reload
    currentModelPath = MODEL_PATH_AOCONGSO;
    switchOutfitButton.textContent = "Ve trang phuc cu";
    await loadModel(currentModelPath);

    updateStatus("Đã tải và đổi trang phục công sở mới thành công!");
  } catch (error) {
    console.error("Upload error:", error);
    updateStatus("Lỗi khi xử lý trang phục: " + error.message);
    alert("Lỗi khi xử lý trang phục: " + error.message);
  } finally {
    uploadClothingBtn.disabled = false;
    uploadClothingBtn.textContent = "Chon file anh ao...";
    uploadClothingInput.value = "";
  }
});

window.addEventListener("resize", fitModelToScreen);

function updateHairColorPanelVisibility() {
  const container = document.getElementById("hairColorContainer");
  if (container) {
    if (hairstyleState === "chibi" || hairstyleState === "chibi2") {
      container.style.display = "block";
    } else {
      container.style.display = "none";
    }
  }
}

// Bind click event listeners to the hair color buttons
const colorButtons = document.querySelectorAll(".color-btn");
colorButtons.forEach(btn => {
  btn.addEventListener("click", async () => {
    if (!model) return;
    
    const selectedColor = btn.getAttribute("data-color");
    if (selectedColor === hairColorState) return;
    
    // Remove active class and reset border on all buttons
    colorButtons.forEach(b => {
      b.classList.remove("active");
      b.style.border = "1px solid rgba(255,255,255,0.2)";
    });
    
    // Add active class and highlight border to clicked button
    btn.classList.add("active");
    btn.style.border = "2px solid #fff";
    
    hairColorState = selectedColor;
    updateStatus(`Đang đổi màu tóc sang ${btn.getAttribute("title")}...`);
    
    try {
      await loadModel(currentModelPath);
      updateStatus(`Đã đổi màu tóc sang ${btn.getAttribute("title")} thành công!`);
    } catch (err) {
      console.error("Color change error:", err);
      updateStatus("Lỗi khi đổi màu tóc: " + err.message);
    }
  });
});

// Toggle sidebar panel
const toggleSidebarButton = document.getElementById("toggleSidebar");
if (toggleSidebarButton) {
  toggleSidebarButton.addEventListener("click", () => {
    const leftPanel = document.querySelector(".left");
    if (leftPanel) {
      leftPanel.classList.toggle("collapsed");
      const isCollapsed = leftPanel.classList.contains("collapsed");
      toggleSidebarButton.innerHTML = isCollapsed ? "☰ Hiện cài đặt" : "✕ Ẩn cài đặt";
      fitModelToScreen();
    }
  });
}

init();
