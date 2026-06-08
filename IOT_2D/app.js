// Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
const LIVE2D_MODEL_DIR = './Backend/haru_greeter_pro_jp/runtime/'; // Directory containing the Live2D model files

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const previewImg = document.getElementById('preview');
const createBtn = document.getElementById('create-btn');
const canvas = document.getElementById('live2d-canvas');
const spinner = document.getElementById('spinner');

let uploadedFile = null;
let pixiApp = null;

// --- Event Listeners ---

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.backgroundColor = '#333';
});
uploadZone.addEventListener('dragleave', () => {
    uploadZone.style.backgroundColor = 'transparent';
});
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.style.backgroundColor = 'transparent';
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

createBtn.addEventListener('click', createCharacter);

// --- Functions ---

/**
 * Handles the selected file, displays a preview, and enables the create button.
 * @param {File} file The image file selected by the user.
 */
function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file.');
        return;
    }
    uploadedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.style.display = 'block';
    };
    reader.readAsDataURL(file);
    createBtn.disabled = false;
}

/**
 * Main function to orchestrate the character creation process.
 */
async function createCharacter() {
    if (!uploadedFile) {
        alert('Please upload an image first.');
        return;
    }

    setLoading(true);

    try {
        // 1. Call /api/analyze to get colors and anime face URL
        console.log('Step 1: Analyzing image...');
        const formData = new FormData();
        formData.append('file', uploadedFile);

        const analyzeResponse = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            body: formData,
        });

        if (!analyzeResponse.ok) {
            const error = await analyzeResponse.json();
            throw new Error(`Analysis failed: ${error.detail}`);
        }
        const { colors } = await analyzeResponse.json();
        console.log('Analysis successful, colors received:', colors);

        // 2. Call /api/patch-texture to get the new texture URL
        console.log('Step 2: Patching texture...');
        const patchResponse = await fetch(`${API_BASE_URL}/api/patch-texture`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(colors),
        });

        if (!patchResponse.ok) {
            const error = await patchResponse.json();
            throw new Error(`Texture patching failed: ${error.detail}`);
        }
        const { texture_url } = await patchResponse.json();
        console.log('Texture patched, new URL:', texture_url);

        // 3. Load the Live2D model with the new texture
        console.log('Step 3: Loading Live2D model...');
        const patchedTextureUrl = `${API_BASE_URL}${texture_url}`;
        await loadLive2DModel(patchedTextureUrl);

    } catch (error) {
        console.error('Character creation process failed:', error);
        alert(`An error occurred: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

/**
 * Loads and displays the Live2D model on the canvas.
 * @param {string} newTextureUrl The URL of the newly patched texture.
 */
async function loadLive2DModel(newTextureUrl) {
    // Initialize Pixi Application if it doesn't exist
    if (!pixiApp) {
        pixiApp = new PIXI.Application({
            view: canvas,
            width: canvas.clientWidth,
            height: canvas.clientHeight,
            autoStart: true,
            backgroundAlpha: 0,
            resizeTo: canvas,
        });
    }

    // Clear previous model if any
    pixiApp.stage.removeChildren();

    // Fetch the model3.json, modify it in memory, and load the model
    const model3JsonPath = `${LIVE2D_MODEL_DIR}model.model3.json`;
    const response = await fetch(model3JsonPath);
    const modelJson = await response.json();

    // IMPORTANT: Override the texture path
    modelJson.FileReferences.Textures[0] = newTextureUrl;

    const model = await PIXI.live2d.Live2DModel.from(modelJson, { autoInteract: true });

    pixiApp.stage.addChild(model);

    // Scale and position the model
    const scale = Math.min(canvas.width / model.width, canvas.height / model.height) * 0.8;
    model.scale.set(scale);
    model.x = (canvas.width - model.width) / 2;
    model.y = (canvas.height - model.height) / 2;

    // Add some interaction
    model.on('hit', (hitAreas) => {
        if (hitAreas.includes('Body')) {
            model.motion('TapBody', undefined, 3);
        }
    });
}

/**
 * Toggles the loading spinner and button state.
 * @param {boolean} isLoading
 */
function setLoading(isLoading) {
    spinner.style.display = isLoading ? 'block' : 'none';
    createBtn.disabled = isLoading;
}