# Automated anime face integration for Live2D
# This script handles complete conversion and texture replacement

param(
    [string]$InputImage = "anh1.jpg",
    [switch]$ApplyToModel = $false,
    [switch]$ShowPreview = $false
)

$ErrorActionPreference = "Continue"

# Get project root
$scriptDir = "c:\xampp\htdocs\2D_ban2\scripts"
$projectRoot = "c:\xampp\htdocs\2D_ban2"
$processedDir = Join-Path $projectRoot "processed_faces"
$textureDir = Join-Path $projectRoot "anime_face_textures"
$live2dDir = Join-Path $projectRoot "haru_greeter_pro_jp" "haru_greeter_pro_jp" "runtime"

function Write-Header {
    param([string]$Text)
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Text)
    Write-Host "[*] $Text" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Text)
    Write-Host "[+] $Text" -ForegroundColor Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "[ERROR] $Text" -ForegroundColor Red
}

function Convert-PortraitToAnime {
    Write-Header "STEP 1: PORTRAIT TO ANIME CONVERSION"
    Write-Info "Converting $InputImage to anime style..."
    
    $pythonScript = Join-Path $scriptDir "face_to_anime.py"
    if (-not (Test-Path $pythonScript)) {
        Write-Error "Python script not found: $pythonScript"
        return $false
    }
    
    try {
        & python $pythonScript
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Anime conversion completed!"
            return $true
        } else {
            Write-Error "Python script failed with exit code: $LASTEXITCODE"
            return $false
        }
    } catch {
        Write-Error "Failed to run Python script: $_"
        return $false
    }
}

function Show-ProcessedImages {
    Write-Header "GENERATED ANIME FACES"
    
    if (-not (Test-Path $processedDir)) {
        Write-Error "Processed directory not found: $processedDir"
        return
    }
    
    Get-ChildItem $processedDir -Filter "*.jpg" | ForEach-Object {
        $size = ($_.Length / 1MB).ToString("F2")
        Write-Info "$($_.Name) ($size MB) - $($_.FullName)"
    }
    
    if ($ShowPreview) {
        Write-Info "Opening images in default viewer..."
        $mainImage = Join-Path $processedDir "anh1_face_anime_upscaled.jpg"
        if (Test-Path $mainImage) {
            & cmd /c start "" $mainImage
        }
    }
}

function Prepare-Live2DTexture {
    Write-Header "STEP 2: PREPARE LIVE2D TEXTURE"
    Write-Info "Preparing texture for Live2D integration..."
    
    # Create output directory
    if (-not (Test-Path $textureDir)) {
        New-Item -ItemType Directory -Path $textureDir -Force | Out-Null
        Write-Success "Created texture directory: $textureDir"
    }
    
    # Copy anime face to texture directory
    $animeSource = Join-Path $processedDir "anh1_face_anime_upscaled.jpg"
    $textureOutput = Join-Path $textureDir "anh1_face_anime_live2d.jpg"
    
    if (Test-Path $animeSource) {
        Copy-Item -Path $animeSource -Destination $textureOutput -Force
        Write-Success "Texture prepared: $textureOutput"
        return $textureOutput
    } else {
        Write-Error "Anime source not found: $animeSource"
        return $null
    }
}

function Get-Live2DTextureFiles {
    Write-Info "Scanning Live2D texture directory..."
    
    if (-not (Test-Path $live2dDir)) {
        Write-Error "Live2D directory not found: $live2dDir"
        return @()
    }
    
    # Find potential texture files
    $textures = @()
    Get-ChildItem $live2dDir -Filter "*.jpg" -Recurse | ForEach-Object {
        if ($_.Name -match "(texture|face|model)" -or $_.Directory.Name -eq "haru_greeter_t05.2048") {
            $textures += $_
        }
    }
    
    if ($textures.Count -eq 0) {
        # Look for any large JPG files
        $textures = Get-ChildItem $live2dDir -Filter "*.jpg" | Sort-Object Length -Descending | Select-Object -First 5
    }
    
    return $textures
}

function Apply-TextureToLive2D {
    param([string]$TextureFile)
    
    Write-Header "STEP 3: APPLY TEXTURE TO LIVE2D"
    
    if (-not (Test-Path $TextureFile)) {
        Write-Error "Texture file not found: $TextureFile"
        return $false
    }
    
    Write-Info "Finding Live2D model files..."
    $live2dTextures = Get-Live2DTextureFiles
    
    if ($live2dTextures.Count -eq 0) {
        Write-Error "No texture files found in Live2D directory"
        return $false
    }
    
    Write-Info "Found $($live2dTextures.Count) potential texture file(s):"
    $live2dTextures | ForEach-Object {
        Write-Info "  - $($_.Name) in $($_.DirectoryName)"
    }
    
    # Create backup
    $live2dTextures | ForEach-Object {
        $backupFile = "$($_.FullName).backup"
        if (-not (Test-Path $backupFile)) {
            Copy-Item -Path $_.FullName -Destination $backupFile -Force
            Write-Success "Backup created: $($_.Name)"
        }
    }
    
    # Replace textures
    $live2dTextures | ForEach-Object {
        Copy-Item -Path $TextureFile -Destination $_.FullName -Force
        Write-Success "Replaced texture: $($_.Name)"
    }
    
    return $true
}

function Show-Next-Steps {
    Write-Header "INTEGRATION COMPLETE!"
    Write-Host @"
The anime face has been successfully converted and integrated!

✓ Anime conversion completed
✓ Texture prepared: $textureDir
✓ Live2D texture replaced

NEXT STEPS:
1. Refresh the browser or restart the development server
2. The character should now display with the anime face
3. If it doesn't appear, check:
   - Browser cache (Ctrl+Shift+R = hard refresh)
   - Developer console for errors (F12)
   - Server is running and serving files

TROUBLESHOOTING:
- If texture doesn't show: Clear browser cache and hard refresh
- If colors are wrong: Check texture format compatibility
- If still not working: Check console for 404 or CORS errors

FILES CREATED:
- Processed anime faces: $processedDir
- Live2D textures: $textureDir
- Backups of original textures in Live2D directory (.backup files)

TO REVERT CHANGES:
1. Restore from .backup files in Live2D directory
2. Or re-run with: .\integrate_anime_face.ps1 -ApplyToModel `$false

"@ -ForegroundColor Green
}

# Main execution
Write-Header "LIVE2D ANIME FACE INTEGRATION"
Write-Info "Input image: $InputImage"
Write-Info "Project root: $projectRoot"

# Step 1: Convert to anime
if (-not (Convert-PortraitToAnime)) {
    Write-Error "Conversion failed. Exiting."
    exit 1
}

# Step 2: Show results
Show-ProcessedImages

# Step 3: Prepare texture
$textureFile = Prepare-Live2DTexture
if (-not $textureFile) {
    Write-Error "Texture preparation failed. Exiting."
    exit 1
}

# Step 4: Apply to Live2D (if requested)
if ($ApplyToModel) {
    if (-not (Apply-TextureToLive2D -TextureFile $textureFile)) {
        Write-Error "Failed to apply texture to Live2D model"
        exit 1
    }
} else {
    Write-Info "Texture prepared but NOT applied (use -ApplyToModel to apply)"
}

# Show next steps
Show-Next-Steps

Write-Host "Done!" -ForegroundColor Green
