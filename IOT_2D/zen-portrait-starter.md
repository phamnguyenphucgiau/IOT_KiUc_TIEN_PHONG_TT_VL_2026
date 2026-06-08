# Zen Portrait Starter

Script `scripts/build-zen-portrait-starter.ps1` tao bo asset starter theo format cua Zen Character Creator 2D tu:

- portrait tham chieu: `anh2.jpg`
- texture mat/toc Live2D: `haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05.2048/texture_00.png`

No sinh ra thu muc:

- `Zen-Character-Creator-2D/Assets/Species/Human/Female/Front Facing/`

Trong do co:

- placeholder `none` cho `Body`, `Blush`, `Jacket`, `Chest`, `Bottom`, `Feet`, `Mask`
- starter `portraitStarter` cho `Head`, `Hair`, `Eyes`, `Lips`, `Neck`
- preview tong hop: `Zen-Character-Creator-2D/Assets/Species/Human/Female/Front Facing/_portraitStarterPreview.png`
- template mac dinh: `Zen-Character-Creator-2D/Assets/Species/Human/Female/defaultCharacterTemplate.zen2dx`

Chay lai script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-zen-portrait-starter.ps1
```

Luu y:

- Zen Character Creator 2D dung `characterFrameSize = 500x550`, nen moi part trong starter pack da duoc dat san vao mot frame trong suot 500x550 va `pos.zen2dpos = 0,0`.
- Repo Zen khong phai thu vien Live2D; no la workflow asset PNG theo tung component. Starter pack nay dung de ban ve lai toc/mat theo format Zen, khong phai convert truc tiep sang moc3.
- Neu ban muon nhan vat giong portrait hon, chinh sua cac file `portraitStarterFill.png` va `portraitStarterOutline.png` trong tung component `Head/Hair/Eyes/Lips/Neck`.
