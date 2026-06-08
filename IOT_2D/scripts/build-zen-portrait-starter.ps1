Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

function Clamp-Channel {
  param([double]$Value)
  return [Math]::Max(0, [Math]::Min(255, [int][Math]::Round($Value)))
}

function New-TransparentBitmap {
  param(
    [int]$Width,
    [int]$Height
  )

  $bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::Transparent)
  }
  finally {
    $graphics.Dispose()
  }
  return $bitmap
}

function Save-Png {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [string]$Path
  )

  $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
}

function Make-WhiteTransparent {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [int]$Threshold = 245
  )

  $out = New-Object System.Drawing.Bitmap($Bitmap.Width, $Bitmap.Height)
  for ($x = 0; $x -lt $Bitmap.Width; $x++) {
    for ($y = 0; $y -lt $Bitmap.Height; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.R -ge $Threshold -and $pixel.G -ge $Threshold -and $pixel.B -ge $Threshold) {
        $out.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
        continue
      }

      $out.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $pixel.R, $pixel.G, $pixel.B))
    }
  }

  return $out
}

function Crop-Transparent {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect
  )

  $crop = New-Object System.Drawing.Bitmap($Rect.Width, $Rect.Height)
  $graphics = [System.Drawing.Graphics]::FromImage($crop)
  try {
    $graphics.DrawImage(
      $Bitmap,
      (New-Object System.Drawing.Rectangle(0, 0, $Rect.Width, $Rect.Height)),
      $Rect,
      [System.Drawing.GraphicsUnit]::Pixel
    )
  }
  finally {
    $graphics.Dispose()
  }

  $transparent = Make-WhiteTransparent -Bitmap $crop
  $crop.Dispose()
  return $transparent
}

function New-SolidFillFromAlpha {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Color]$Color
  )

  $fill = New-Object System.Drawing.Bitmap($Bitmap.Width, $Bitmap.Height)
  for ($x = 0; $x -lt $Bitmap.Width; $x++) {
    for ($y = 0; $y -lt $Bitmap.Height; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8) {
        $fill.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
        continue
      }

      $fill.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($pixel.A, $Color.R, $Color.G, $Color.B))
    }
  }

  return $fill
}

function Multiply-TintBitmap {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Color]$Tint,
    [double]$Amount = 0.4
  )

  $tinted = New-Object System.Drawing.Bitmap($Bitmap.Width, $Bitmap.Height)
  for ($x = 0; $x -lt $Bitmap.Width; $x++) {
    for ($y = 0; $y -lt $Bitmap.Height; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8) {
        $tinted.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
        continue
      }

      $r = Clamp-Channel (($pixel.R * (1 - $Amount)) + ($Tint.R * $Amount))
      $g = Clamp-Channel (($pixel.G * (1 - $Amount)) + ($Tint.G * $Amount))
      $b = Clamp-Channel (($pixel.B * (1 - $Amount)) + ($Tint.B * $Amount))
      $tinted.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($pixel.A, $r, $g, $b))
    }
  }

  return $tinted
}

function Copy-Bitmap {
  param([System.Drawing.Bitmap]$Bitmap)
  return New-Object System.Drawing.Bitmap($Bitmap)
}

function Get-AverageColor {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect
  )

  $sumR = 0.0
  $sumG = 0.0
  $sumB = 0.0
  $count = 0.0

  for ($x = $Rect.Left; $x -lt [Math]::Min($Rect.Right, $Bitmap.Width); $x++) {
    for ($y = $Rect.Top; $y -lt [Math]::Min($Rect.Bottom, $Bitmap.Height); $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      $sumR += $pixel.R
      $sumG += $pixel.G
      $sumB += $pixel.B
      $count += 1
    }
  }

  if ($count -eq 0) {
    return [System.Drawing.Color]::White
  }

  return [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($sumR / $count)),
    (Clamp-Channel ($sumG / $count)),
    (Clamp-Channel ($sumB / $count))
  )
}

function Draw-Layer {
  param(
    [System.Drawing.Graphics]$Graphics,
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Destination
  )

  $Graphics.DrawImage(
    $Bitmap,
    $Destination,
    (New-Object System.Drawing.Rectangle(0, 0, $Bitmap.Width, $Bitmap.Height)),
    [System.Drawing.GraphicsUnit]::Pixel
  )
}

function Save-AssetSet {
  param(
    [string]$ComponentPath,
    [string]$AssetName,
    [System.Drawing.Bitmap]$FillBitmap,
    [System.Drawing.Bitmap]$OutlineBitmap,
    [int]$PosX = 0,
    [int]$PosY = 0
  )

  $assetPath = Join-Path $ComponentPath $AssetName
  Ensure-Directory $assetPath

  $fillPath = Join-Path $assetPath ($AssetName + "Fill.png")
  $outlinePath = Join-Path $assetPath ($AssetName + "Outline.png")
  $thumbPath = Join-Path $assetPath ($AssetName + "Thumbnail.png")
  $posPath = Join-Path $assetPath "pos.zen2dpos"

  Save-Png -Bitmap $FillBitmap -Path $fillPath
  Save-Png -Bitmap $OutlineBitmap -Path $outlinePath

  $thumb = New-Object System.Drawing.Bitmap(110, 110)
  $graphics = [System.Drawing.Graphics]::FromImage($thumb)
  try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.DrawImage($OutlineBitmap, 0, 0, 110, 110)
  }
  finally {
    $graphics.Dispose()
  }
  Save-Png -Bitmap $thumb -Path $thumbPath
  $thumb.Dispose()

  @(
    "x=$PosX"
    "y=$PosY"
  ) | Set-Content -LiteralPath $posPath
}

$root = Split-Path -Parent $PSScriptRoot
$atlasPath = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05.2048\texture_00.png"
$portraitPath = Join-Path $root "anh2.jpg"
$zenFrontFacing = Join-Path $root "Zen-Character-Creator-2D\Assets\Species\Human\Female\Front Facing"

Ensure-Directory (Join-Path $root "Zen-Character-Creator-2D\Assets")
Ensure-Directory (Join-Path $root "Zen-Character-Creator-2D\Assets\Species")
Ensure-Directory (Join-Path $root "Zen-Character-Creator-2D\Assets\Species\Human")
Ensure-Directory (Join-Path $root "Zen-Character-Creator-2D\Assets\Species\Human\Female")
Ensure-Directory $zenFrontFacing

$components = @("Body", "Eyes", "Lips", "Blush", "Head", "Neck", "Jacket", "Chest", "Bottom", "Feet", "Mask", "Hair")
foreach ($component in $components) {
  Ensure-Directory (Join-Path $zenFrontFacing $component)
}

$frameW = 500
$frameH = 550

$atlas = [System.Drawing.Bitmap]::FromFile($atlasPath)
$portrait = [System.Drawing.Bitmap]::FromFile($portraitPath)

$disposables = New-Object System.Collections.Generic.List[System.IDisposable]
$disposables.Add($atlas) | Out-Null
$disposables.Add($portrait) | Out-Null

try {
  $skinBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.36),
    [int]($portrait.Height * 0.22),
    [int]($portrait.Width * 0.22),
    [int]($portrait.Height * 0.20)
  ))
  $hairBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.28),
    [int]($portrait.Height * 0.04),
    [int]($portrait.Width * 0.32),
    [int]($portrait.Height * 0.18)
  ))
  $lipBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.42),
    [int]($portrait.Height * 0.49),
    [int]($portrait.Width * 0.10),
    [int]($portrait.Height * 0.05)
  ))
  $skinSample = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel (($skinBase.R * 0.35) + 152)),
    (Clamp-Channel (($skinBase.G * 0.35) + 134)),
    (Clamp-Channel (($skinBase.B * 0.35) + 126))
  )
  $hairSample = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel (($hairBase.R * 0.45) + 58)),
    (Clamp-Channel (($hairBase.G * 0.45) + 39)),
    (Clamp-Channel (($hairBase.B * 0.45) + 33))
  )
  $lipSample = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel (($lipBase.R * 0.35) + 118)),
    (Clamp-Channel (($lipBase.G * 0.35) + 74)),
    (Clamp-Channel (($lipBase.B * 0.35) + 86))
  )

  $faceBase = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1202, 25, 392, 527))
  $hairFront = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1416, 502, 299, 167))
  $hairBack = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1235, 534, 261, 264))
  $hairSide = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1100, 457, 106, 506))
  $browLeft = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1235, 990, 138, 26))
  $browRight = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1431, 987, 138, 26))
  $eyeLeft = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1243, 1050, 130, 44))
  $eyeRight = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1434, 1054, 130, 45))
  $pupilLeft = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1281, 1085, 31, 54))
  $pupilRight = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1497, 1089, 33, 54))
  $mouth = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1219, 818, 130, 68))
  $nose = Crop-Transparent -Bitmap $atlas -Rect (New-Object System.Drawing.Rectangle(1380, 829, 54, 57))
  $hairSideMirror = Copy-Bitmap -Bitmap $hairSide
  $hairSideMirror.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipX)

  foreach ($bitmap in @($faceBase, $hairFront, $hairBack, $hairSide, $hairSideMirror, $browLeft, $browRight, $eyeLeft, $eyeRight, $pupilLeft, $pupilRight, $mouth, $nose)) {
    $disposables.Add($bitmap) | Out-Null
  }

  $faceBaseTinted = Multiply-TintBitmap -Bitmap $faceBase -Tint $skinSample -Amount 0.26
  $hairFrontTinted = Multiply-TintBitmap -Bitmap $hairFront -Tint $hairSample -Amount 0.34
  $hairBackTinted = Multiply-TintBitmap -Bitmap $hairBack -Tint $hairSample -Amount 0.34
  $mouthTinted = Multiply-TintBitmap -Bitmap $mouth -Tint $lipSample -Amount 0.28

  foreach ($bitmap in @($faceBaseTinted, $hairFrontTinted, $hairBackTinted, $mouthTinted)) {
    $disposables.Add($bitmap) | Out-Null
  }

  $blankFrame = New-TransparentBitmap -Width $frameW -Height $frameH
  $disposables.Add($blankFrame) | Out-Null

  foreach ($component in @("Body", "Blush", "Jacket", "Chest", "Bottom", "Feet", "Mask")) {
    Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing $component) -AssetName "none" -FillBitmap $blankFrame -OutlineBitmap $blankFrame
  }

  $skinShadow = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($skinSample.R * 0.86)),
    (Clamp-Channel ($skinSample.G * 0.84)),
    (Clamp-Channel ($skinSample.B * 0.84))
  )
  $skinHighlight = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($skinSample.R * 1.04)),
    (Clamp-Channel ($skinSample.G * 1.03)),
    (Clamp-Channel ($skinSample.B * 1.03))
  )
  $hairDark = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairSample.R * 0.62)),
    (Clamp-Channel ($hairSample.G * 0.62)),
    (Clamp-Channel ($hairSample.B * 0.62))
  )
  $hairLight = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairSample.R * 1.18)),
    (Clamp-Channel ($hairSample.G * 1.16)),
    (Clamp-Channel ($hairSample.B * 1.12))
  )
  $outlineColor = [System.Drawing.Color]::FromArgb(255, 86, 63, 60)
  $browColor = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairDark.R * 0.90)),
    (Clamp-Channel ($hairDark.G * 0.84)),
    (Clamp-Channel ($hairDark.B * 0.84))
  )
  $irisColor = [System.Drawing.Color]::FromArgb(255, 92, 54, 46)
  $lipDeep = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($lipSample.R * 0.92)),
    (Clamp-Channel ($lipSample.G * 0.76)),
    (Clamp-Channel ($lipSample.B * 0.84))
  )

  $headSilhouette = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(250, 72)),
    (New-Object System.Drawing.Point(206, 82)),
    (New-Object System.Drawing.Point(175, 114)),
    (New-Object System.Drawing.Point(162, 164)),
    (New-Object System.Drawing.Point(166, 228)),
    (New-Object System.Drawing.Point(182, 286)),
    (New-Object System.Drawing.Point(204, 332)),
    (New-Object System.Drawing.Point(225, 356)),
    (New-Object System.Drawing.Point(250, 368)),
    (New-Object System.Drawing.Point(275, 356)),
    (New-Object System.Drawing.Point(296, 332)),
    (New-Object System.Drawing.Point(318, 286)),
    (New-Object System.Drawing.Point(334, 228)),
    (New-Object System.Drawing.Point(338, 164)),
    (New-Object System.Drawing.Point(325, 114)),
    (New-Object System.Drawing.Point(294, 82))
  )
  $jawShadow = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(182, 246)),
    (New-Object System.Drawing.Point(202, 302)),
    (New-Object System.Drawing.Point(246, 340)),
    (New-Object System.Drawing.Point(292, 306)),
    (New-Object System.Drawing.Point(312, 252)),
    (New-Object System.Drawing.Point(286, 304)),
    (New-Object System.Drawing.Point(250, 326)),
    (New-Object System.Drawing.Point(214, 304))
  )

  $headFrameFill = New-TransparentBitmap -Width $frameW -Height $frameH
  $headFrameOutline = New-TransparentBitmap -Width $frameW -Height $frameH
  foreach ($bitmap in @($headFrameFill, $headFrameOutline)) {
    $disposables.Add($bitmap) | Out-Null
  }
  $graphics = [System.Drawing.Graphics]::FromImage($headFrameFill)
  $graphicsOutline = [System.Drawing.Graphics]::FromImage($headFrameOutline)
  try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphicsOutline.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

    $fillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $skinBrush = New-Object System.Drawing.SolidBrush($skinSample)
    $jawBrush = New-Object System.Drawing.SolidBrush($skinShadow)
    $highlightBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(85, $skinHighlight.R, $skinHighlight.G, $skinHighlight.B))
    $outlinePen = New-Object System.Drawing.Pen($outlineColor, 4)
    $nosePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(180, 146, 112, 108), 3)
    $mouthGuidePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(120, 126, 102, 100), 2)
    try {
      $graphics.FillPolygon($fillBrush, $headSilhouette)

      $graphicsOutline.FillPolygon($skinBrush, $headSilhouette)
      $graphicsOutline.FillPolygon($jawBrush, $jawShadow)
      $graphicsOutline.FillEllipse($highlightBrush, 186, 102, 112, 76)
      $graphicsOutline.DrawPolygon($outlinePen, $headSilhouette)
      $graphicsOutline.DrawCurve($nosePen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(253, 204)),
        (New-Object System.Drawing.Point(246, 234)),
        (New-Object System.Drawing.Point(244, 264)),
        (New-Object System.Drawing.Point(252, 286))
      ))
      $graphicsOutline.DrawArc($nosePen, 234, 280, 34, 18, 8, 160)
      $graphicsOutline.DrawArc($mouthGuidePen, 226, 320, 48, 10, 12, 156)
    }
    finally {
      $fillBrush.Dispose()
      $skinBrush.Dispose()
      $jawBrush.Dispose()
      $highlightBrush.Dispose()
      $outlinePen.Dispose()
      $nosePen.Dispose()
      $mouthGuidePen.Dispose()
    }
  }
  finally {
    $graphics.Dispose()
    $graphicsOutline.Dispose()
  }
  Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing "Head") -AssetName "portraitStarter" -FillBitmap $headFrameFill -OutlineBitmap $headFrameOutline

  $hairBackShape = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(182, 84)),
    (New-Object System.Drawing.Point(146, 126)),
    (New-Object System.Drawing.Point(132, 188)),
    (New-Object System.Drawing.Point(132, 250)),
    (New-Object System.Drawing.Point(144, 318)),
    (New-Object System.Drawing.Point(132, 382)),
    (New-Object System.Drawing.Point(154, 432)),
    (New-Object System.Drawing.Point(186, 406)),
    (New-Object System.Drawing.Point(201, 332)),
    (New-Object System.Drawing.Point(215, 414)),
    (New-Object System.Drawing.Point(250, 440)),
    (New-Object System.Drawing.Point(286, 414)),
    (New-Object System.Drawing.Point(300, 332)),
    (New-Object System.Drawing.Point(316, 406)),
    (New-Object System.Drawing.Point(346, 432)),
    (New-Object System.Drawing.Point(370, 382)),
    (New-Object System.Drawing.Point(358, 318)),
    (New-Object System.Drawing.Point(370, 250)),
    (New-Object System.Drawing.Point(368, 182)),
    (New-Object System.Drawing.Point(352, 124)),
    (New-Object System.Drawing.Point(318, 84)),
    (New-Object System.Drawing.Point(282, 64)),
    (New-Object System.Drawing.Point(218, 60))
  )
  $hairFaceOpening = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(192, 122)),
    (New-Object System.Drawing.Point(178, 164)),
    (New-Object System.Drawing.Point(178, 222)),
    (New-Object System.Drawing.Point(190, 278)),
    (New-Object System.Drawing.Point(208, 320)),
    (New-Object System.Drawing.Point(228, 346)),
    (New-Object System.Drawing.Point(250, 358)),
    (New-Object System.Drawing.Point(272, 346)),
    (New-Object System.Drawing.Point(292, 320)),
    (New-Object System.Drawing.Point(310, 278)),
    (New-Object System.Drawing.Point(322, 222)),
    (New-Object System.Drawing.Point(322, 164)),
    (New-Object System.Drawing.Point(308, 122)),
    (New-Object System.Drawing.Point(286, 106)),
    (New-Object System.Drawing.Point(214, 106))
  )
  $hairTopShape = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(176, 118)),
    (New-Object System.Drawing.Point(200, 78)),
    (New-Object System.Drawing.Point(248, 58)),
    (New-Object System.Drawing.Point(304, 68)),
    (New-Object System.Drawing.Point(344, 96)),
    (New-Object System.Drawing.Point(334, 132)),
    (New-Object System.Drawing.Point(292, 120)),
    (New-Object System.Drawing.Point(266, 128)),
    (New-Object System.Drawing.Point(246, 154)),
    (New-Object System.Drawing.Point(228, 132))
  )
  $hairFringeShape = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(188, 138)),
    (New-Object System.Drawing.Point(210, 114)),
    (New-Object System.Drawing.Point(246, 120)),
    (New-Object System.Drawing.Point(268, 100)),
    (New-Object System.Drawing.Point(312, 112)),
    (New-Object System.Drawing.Point(326, 148)),
    (New-Object System.Drawing.Point(302, 140)),
    (New-Object System.Drawing.Point(284, 158)),
    (New-Object System.Drawing.Point(250, 150)),
    (New-Object System.Drawing.Point(224, 172)),
    (New-Object System.Drawing.Point(204, 162))
  )
  $leftFrameShape = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(170, 170)),
    (New-Object System.Drawing.Point(152, 206)),
    (New-Object System.Drawing.Point(146, 264)),
    (New-Object System.Drawing.Point(154, 326)),
    (New-Object System.Drawing.Point(176, 314)),
    (New-Object System.Drawing.Point(188, 250)),
    (New-Object System.Drawing.Point(194, 190))
  )
  $rightFrameShape = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(330, 164)),
    (New-Object System.Drawing.Point(348, 200)),
    (New-Object System.Drawing.Point(354, 258)),
    (New-Object System.Drawing.Point(346, 320)),
    (New-Object System.Drawing.Point(324, 308)),
    (New-Object System.Drawing.Point(312, 244)),
    (New-Object System.Drawing.Point(306, 186))
  )

  $hairFrameFill = New-TransparentBitmap -Width $frameW -Height $frameH
  $hairFrameOutline = New-TransparentBitmap -Width $frameW -Height $frameH
  foreach ($bitmap in @($hairFrameFill, $hairFrameOutline)) {
    $disposables.Add($bitmap) | Out-Null
  }
  $graphics = [System.Drawing.Graphics]::FromImage($hairFrameFill)
  $graphicsOutline = [System.Drawing.Graphics]::FromImage($hairFrameOutline)
  try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphicsOutline.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

    $fillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $hairBrush = New-Object System.Drawing.SolidBrush($hairSample)
    $hairDarkBrush = New-Object System.Drawing.SolidBrush($hairDark)
    $clearBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::Transparent)
    $highlightPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(160, $hairLight.R, $hairLight.G, $hairLight.B), 4)
    $outlinePen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 70, 52, 48), 4)
    try {
      $graphics.FillPolygon($fillBrush, $hairBackShape)
      $graphicsOutline.FillPolygon($hairDarkBrush, $hairBackShape)

      $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
      $graphicsOutline.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
      $graphics.FillPolygon($clearBrush, $hairFaceOpening)
      $graphicsOutline.FillPolygon($clearBrush, $hairFaceOpening)
      $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
      $graphicsOutline.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver

      foreach ($shape in @($hairTopShape, $hairFringeShape, $leftFrameShape, $rightFrameShape)) {
        $graphics.FillPolygon($fillBrush, $shape)
      }

      $graphicsOutline.FillPolygon($hairBrush, $hairTopShape)
      $graphicsOutline.FillPolygon($hairDarkBrush, $hairFringeShape)
      $graphicsOutline.FillPolygon($hairBrush, $leftFrameShape)
      $graphicsOutline.FillPolygon($hairBrush, $rightFrameShape)

      foreach ($shape in @($hairBackShape, $hairTopShape, $hairFringeShape, $leftFrameShape, $rightFrameShape)) {
        $graphicsOutline.DrawPolygon($outlinePen, $shape)
      }

      $graphicsOutline.DrawCurve($highlightPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(218, 88)),
        (New-Object System.Drawing.Point(232, 126)),
        (New-Object System.Drawing.Point(244, 166))
      ))
      $graphicsOutline.DrawCurve($highlightPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(286, 84)),
        (New-Object System.Drawing.Point(300, 122)),
        (New-Object System.Drawing.Point(308, 160))
      ))
      $graphicsOutline.DrawCurve($highlightPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(184, 192)),
        (New-Object System.Drawing.Point(178, 246)),
        (New-Object System.Drawing.Point(170, 304))
      ))
      $graphicsOutline.DrawCurve($highlightPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(316, 188)),
        (New-Object System.Drawing.Point(322, 242)),
        (New-Object System.Drawing.Point(330, 300))
      ))
    }
    finally {
      $fillBrush.Dispose()
      $hairBrush.Dispose()
      $hairDarkBrush.Dispose()
      $clearBrush.Dispose()
      $highlightPen.Dispose()
      $outlinePen.Dispose()
    }
  }
  finally {
    $graphics.Dispose()
    $graphicsOutline.Dispose()
  }
  Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing "Hair") -AssetName "portraitStarter" -FillBitmap $hairFrameFill -OutlineBitmap $hairFrameOutline

  $eyesFrameFill = New-TransparentBitmap -Width $frameW -Height $frameH
  $eyesFrameOutline = New-TransparentBitmap -Width $frameW -Height $frameH
  foreach ($bitmap in @($eyesFrameFill, $eyesFrameOutline)) {
    $disposables.Add($bitmap) | Out-Null
  }
  $graphics = [System.Drawing.Graphics]::FromImage($eyesFrameFill)
  $graphicsOutline = [System.Drawing.Graphics]::FromImage($eyesFrameOutline)
  try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphicsOutline.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

    $eyeFillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $scleraBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 250, 246, 242))
    $irisBrush = New-Object System.Drawing.SolidBrush($irisColor)
    $pupilBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 28, 22, 24))
    $browPen = New-Object System.Drawing.Pen($browColor, 6)
    $upperLidPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 62, 40, 44), 4)
    $lowerLidPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(180, 98, 72, 74), 2)
    try {
      $graphics.FillEllipse($eyeFillBrush, 180, 238, 54, 18)
      $graphics.FillEllipse($eyeFillBrush, 266, 238, 54, 18)

      $graphicsOutline.FillEllipse($scleraBrush, 180, 238, 54, 18)
      $graphicsOutline.FillEllipse($scleraBrush, 266, 238, 54, 18)
      $graphicsOutline.FillEllipse($irisBrush, 200, 239, 12, 14)
      $graphicsOutline.FillEllipse($irisBrush, 286, 239, 12, 14)
      $graphicsOutline.FillEllipse($pupilBrush, 204, 242, 5, 7)
      $graphicsOutline.FillEllipse($pupilBrush, 290, 242, 5, 7)
      $graphicsOutline.FillEllipse($eyeFillBrush, 202, 240, 2, 2)
      $graphicsOutline.FillEllipse($eyeFillBrush, 288, 240, 2, 2)
      $graphicsOutline.DrawCurve($browPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(178, 214)),
        (New-Object System.Drawing.Point(206, 205)),
        (New-Object System.Drawing.Point(238, 208))
      ))
      $graphicsOutline.DrawCurve($browPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(262, 208)),
        (New-Object System.Drawing.Point(294, 204)),
        (New-Object System.Drawing.Point(322, 214))
      ))
      $graphicsOutline.DrawCurve($upperLidPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(180, 248)),
        (New-Object System.Drawing.Point(206, 232)),
        (New-Object System.Drawing.Point(232, 246))
      ))
      $graphicsOutline.DrawCurve($upperLidPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(268, 246)),
        (New-Object System.Drawing.Point(294, 230)),
        (New-Object System.Drawing.Point(320, 248))
      ))
      $graphicsOutline.DrawCurve($lowerLidPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(186, 250)),
        (New-Object System.Drawing.Point(206, 258)),
        (New-Object System.Drawing.Point(226, 250))
      ))
      $graphicsOutline.DrawCurve($lowerLidPen, [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(274, 250)),
        (New-Object System.Drawing.Point(294, 258)),
        (New-Object System.Drawing.Point(314, 250))
      ))
    }
    finally {
      $eyeFillBrush.Dispose()
      $scleraBrush.Dispose()
      $irisBrush.Dispose()
      $pupilBrush.Dispose()
      $browPen.Dispose()
      $upperLidPen.Dispose()
      $lowerLidPen.Dispose()
    }
  }
  finally {
    $graphics.Dispose()
    $graphicsOutline.Dispose()
  }
  Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing "Eyes") -AssetName "portraitStarter" -FillBitmap $eyesFrameFill -OutlineBitmap $eyesFrameOutline

  $lipsFrameFill = New-TransparentBitmap -Width $frameW -Height $frameH
  $lipsFrameOutline = New-TransparentBitmap -Width $frameW -Height $frameH
  foreach ($bitmap in @($lipsFrameFill, $lipsFrameOutline)) {
    $disposables.Add($bitmap) | Out-Null
  }
  $graphics = [System.Drawing.Graphics]::FromImage($lipsFrameFill)
  $graphicsOutline = [System.Drawing.Graphics]::FromImage($lipsFrameOutline)
  try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphicsOutline.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $lipFillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $lipBrush = New-Object System.Drawing.SolidBrush($lipDeep)
    $lipShadowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, (Clamp-Channel ($lipDeep.R * 0.82)), (Clamp-Channel ($lipDeep.G * 0.82)), (Clamp-Channel ($lipDeep.B * 0.82))))
    $lipPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(180, 118, 76, 84), 2)
    try {
      $topLip = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(220, 318)),
        (New-Object System.Drawing.Point(234, 310)),
        (New-Object System.Drawing.Point(246, 314)),
        (New-Object System.Drawing.Point(250, 320)),
        (New-Object System.Drawing.Point(254, 314)),
        (New-Object System.Drawing.Point(266, 310)),
        (New-Object System.Drawing.Point(280, 318)),
        (New-Object System.Drawing.Point(266, 322)),
        (New-Object System.Drawing.Point(250, 325)),
        (New-Object System.Drawing.Point(234, 322))
      )
      $bottomLip = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(224, 323)),
        (New-Object System.Drawing.Point(250, 334)),
        (New-Object System.Drawing.Point(276, 323)),
        (New-Object System.Drawing.Point(268, 337)),
        (New-Object System.Drawing.Point(250, 342)),
        (New-Object System.Drawing.Point(232, 337))
      )

      $graphics.FillPolygon($lipFillBrush, $topLip)
      $graphics.FillPolygon($lipFillBrush, $bottomLip)

      $graphicsOutline.FillPolygon($lipShadowBrush, $topLip)
      $graphicsOutline.FillPolygon($lipBrush, $bottomLip)
      $graphicsOutline.DrawPolygon($lipPen, $topLip)
      $graphicsOutline.DrawPolygon($lipPen, $bottomLip)
    }
    finally {
      $lipFillBrush.Dispose()
      $lipBrush.Dispose()
      $lipShadowBrush.Dispose()
      $lipPen.Dispose()
    }
  }
  finally {
    $graphics.Dispose()
    $graphicsOutline.Dispose()
  }
  Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing "Lips") -AssetName "portraitStarter" -FillBitmap $lipsFrameFill -OutlineBitmap $lipsFrameOutline

  $neckFrameFill = New-TransparentBitmap -Width $frameW -Height $frameH
  $neckFrameOutline = New-TransparentBitmap -Width $frameW -Height $frameH
  foreach ($bitmap in @($neckFrameFill, $neckFrameOutline)) {
    $disposables.Add($bitmap) | Out-Null
  }
  $graphics = [System.Drawing.Graphics]::FromImage($neckFrameFill)
  $graphicsOutline = [System.Drawing.Graphics]::FromImage($neckFrameOutline)
  try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphicsOutline.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $neckFillBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $neckBrush = New-Object System.Drawing.SolidBrush($skinSample)
    $neckShadowBrush = New-Object System.Drawing.SolidBrush($skinShadow)
    $neckPen = New-Object System.Drawing.Pen($outlineColor, 3)
    try {
      $neckShape = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(222, 340)),
        (New-Object System.Drawing.Point(278, 340)),
        (New-Object System.Drawing.Point(288, 432)),
        (New-Object System.Drawing.Point(212, 432))
      )
      $neckShadow = [System.Drawing.Point[]]@(
        (New-Object System.Drawing.Point(238, 342)),
        (New-Object System.Drawing.Point(262, 342)),
        (New-Object System.Drawing.Point(254, 404)),
        (New-Object System.Drawing.Point(246, 404))
      )

      $graphics.FillPolygon($neckFillBrush, $neckShape)
      $graphicsOutline.FillPolygon($neckBrush, $neckShape)
      $graphicsOutline.FillPolygon($neckShadowBrush, $neckShadow)
      $graphicsOutline.DrawPolygon($neckPen, $neckShape)
    }
    finally {
      $neckFillBrush.Dispose()
      $neckBrush.Dispose()
      $neckShadowBrush.Dispose()
      $neckPen.Dispose()
    }
  }
  finally {
    $graphics.Dispose()
    $graphicsOutline.Dispose()
  }
  Save-AssetSet -ComponentPath (Join-Path $zenFrontFacing "Neck") -AssetName "portraitStarter" -FillBitmap $neckFrameFill -OutlineBitmap $neckFrameOutline

  $templatePath = Join-Path (Join-Path $root "Zen-Character-Creator-2D\Assets\Species\Human\Female") "defaultCharacterTemplate.zen2dx"
  @(
    "::Species=Human::Gender=Female::Pose=Front Facing::"
    "Body=[Single]none,#764c39"
    "Eyes=[Single]portraitStarter,#6b4e43"
    "Lips=[Single]portraitStarter,#b26f7d"
    "Blush=[Single]none,#f1c0c7"
    "Head=[Single]portraitStarter,#ffffff"
    "Neck=[Single]portraitStarter,#dcc5bc"
    "Jacket=[Single]none,#b5b5b5"
    "Chest=[Single]none,#b5b5b5"
    "Bottom=[Single]none,#b5b5b5"
    "Feet=[Single]none,#000000"
    "Mask=[Single]none,#b5b5b5"
    "Hair=[Single]portraitStarter,#5a463f"
  ) | Set-Content -LiteralPath $templatePath

  $preview = New-TransparentBitmap -Width $frameW -Height $frameH
  $disposables.Add($preview) | Out-Null
  $graphics = [System.Drawing.Graphics]::FromImage($preview)
  try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.DrawImage($neckFrameOutline, 0, 0)
    $graphics.DrawImage($headFrameOutline, 0, 0)
    $graphics.DrawImage($hairFrameOutline, 0, 0)
    $graphics.DrawImage($eyesFrameOutline, 0, 0)
    $graphics.DrawImage($lipsFrameOutline, 0, 0)
  }
  finally {
    $graphics.Dispose()
  }
  Save-Png -Bitmap $preview -Path (Join-Path $zenFrontFacing "_portraitStarterPreview.png")
}
finally {
  foreach ($item in $disposables) {
    $item.Dispose()
  }
}
