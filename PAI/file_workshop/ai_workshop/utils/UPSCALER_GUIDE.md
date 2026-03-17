# Image Upscaler — User Guide
### File Workshop AI · utils/upscaler.py

---

## What is the Image Upscaler?

The Image Upscaler enlarges your images to a higher resolution using
high-quality resampling algorithms. It does **not** require a GPU or
any AI model — it runs entirely on your CPU using Pillow.

You can upscale a single image or an entire batch at once.

---

## How to Use It

### Step 1 — Add your images
Click **+ Add Files** in the top bar or sidebar.
Supported formats: PNG · JPG · JPEG · WEBP · BMP · GIF · TIFF · ICO

### Step 2 — Open the Upscale tab
Click **🖼 Upscale** in the left sidebar.

### Step 3 — Configure settings

| Setting | What it does |
|---------|-------------|
| **Scale factor** | How much to enlarge: 1.5× · 2× · 3× · 4× or custom |
| **Algorithm** | The resampling method (see guide below) |
| **Sharpness boost** | Post-upscale sharpening (None / Light / Medium / Strong) |
| **Denoise** | Reduces grain/noise before upscaling (good for old scans) |
| **File suffix** | Text appended to output filename (default: `_upscaled`) |

### Step 4 — Preview Info (optional)
Click **🔍 Preview Info** to see the current dimensions, color mode,
and file size of your loaded images before processing.

### Step 5 — Run
Click **▶ UPSCALE IMAGES**. Output is saved to your output folder.
A progress bar tracks each image.

### Step 6 — AI Recommendation (optional)
Click **🤖 AI Recommend** and the AI will analyse your image specs
and suggest the best algorithm and scale factor for your use case.

---

## Choosing the Right Algorithm

### 🏆 Lanczos — Best general quality
- **Best for:** Photos, documents, screenshots, anything with fine detail
- **How it works:** Uses a sinc-based filter that preserves sharpness
  while avoiding blocky or blurry artefacts
- **Trade-off:** Slightly slower than bicubic/bilinear
- **Recommended when in doubt**

### 🎨 Bicubic — Smooth results
- **Best for:** Illustrations, vector-style graphics, logos, diagrams
- **How it works:** Uses cubic interpolation over a 4×4 neighbourhood
- **Trade-off:** Can appear slightly softer than Lanczos on photos
- **Good default for non-photographic images**

### ⚡ Bilinear — Fast and general
- **Best for:** Quick previews, large batches where speed matters
- **How it works:** Linear interpolation over a 2×2 neighbourhood
- **Trade-off:** Lower quality than Lanczos/Bicubic, softer result
- **Use when processing speed is the priority**

### 🎮 Nearest Neighbour — Pixel-perfect
- **Best for:** Pixel art, sprites, retro game graphics, QR codes
- **How it works:** Copies the nearest source pixel — no blending
- **Trade-off:** Produces blocky results on photos
- **Only use for content that should have hard pixel edges**

### 📄 Edge Enhance — Text and scans
- **Best for:** Scanned documents, text images, whiteboards, slides
- **How it works:** Lanczos upscale + edge sharpening + edge enhancement
- **Trade-off:** Can over-sharpen smooth gradients
- **Ideal for making scanned text more readable**

---

## Scale Factor Guide

| Factor | Use case | Example |
|--------|----------|---------|
| **1.5×** | Minor upscale, slightly larger display size | 800×600 → 1200×900 |
| **2×** | Most common — doubles resolution | 1080p → 4K equivalent |
| **3×** | Significant enlargement for print | 500×500 → 1500×1500 |
| **4×** | Maximum quality enlargement | Thumbnails → full-size |
| **Custom** | Exact control, e.g. 2.5× or 1.8× | Any ratio from 1.1× to 8× |

> **Note:** Upscaling always increases file size significantly.
> A 2× upscale produces an image with 4× as many pixels.

---

## Sharpness Boost

After upscaling, a sharpness enhancer can be applied:

| Level | Enhancement factor | When to use |
|-------|-------------------|-------------|
| **None** | 1.0× | Image is already sharp, or using Edge Enhance algorithm |
| **Light** | 1.3× | Slight crispness improvement for Bicubic/Bilinear |
| **Medium** | 1.6× | Good general boost after Lanczos on photos |
| **Strong** | 2.0× | Scanned documents, low-quality source images |

> Too much sharpening on smooth images creates unwanted halos.

---

## Denoise Option

When checked, a **median blur (3×3)** is applied to the image
**before** upscaling. This:

- Removes film grain and sensor noise
- Smooths JPEG compression artefacts
- Cleans up old scanned documents

**Do not use** for pixel art or images where fine detail matters.

---

## Output Files

Output images are saved to your configured **Output Folder** with
the suffix appended to the original filename.

Example:
```
Input:   photo.jpg
Suffix:  _upscaled
Output:  photo_upscaled.jpg  (in output folder)
```

The original file is **never modified**.

---

## Supported Input Formats

| Format | Extension |
|--------|-----------|
| PNG (recommended) | .png |
| JPEG | .jpg, .jpeg |
| WebP | .webp |
| BMP | .bmp |
| GIF (first frame) | .gif |
| TIFF | .tiff, .tif |
| ICO | .ico |

---

## Supported Output Formats

The output format matches the input format automatically.
- JPEG output uses quality=95 (near-lossless)
- PNG output is lossless
- RGBA images converted to JPEG will have white background applied

---

## Requirements

Only **Pillow** is required:
```bash
pip install Pillow
```

No GPU, no CUDA, no external models needed.

---

## Tips and Best Practices

1. **Always check the original first** — use 🔍 Preview Info to
   see if the source image is worth upscaling.

2. **2× Lanczos is the sweet spot** for most use cases.
   It doubles resolution with excellent quality.

3. **Don't upscale already-compressed JPEGs** repeatedly —
   each re-save degrades quality. Upscale once from the best
   available source.

4. **For print work**, use 300 DPI as your target.
   If printing at 10cm × 10cm, you need ~1181×1181 pixels.
   Calculate your required scale accordingly.

5. **Batch processing**: Add multiple images to the queue and
   run once — all are processed with the same settings.

6. **Ask the AI**: Click 🤖 AI Recommend for personalised
   advice based on your specific image's dimensions and type.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "pip install Pillow" error | Run: `pip install Pillow` |
| Output looks blurry | Try Lanczos + Light sharpening |
| Output looks oversharpened | Reduce sharpness to None or Light |
| Pixel art looks blurry | Switch algorithm to Nearest Neighbour |
| Scanned text still unclear | Use Edge Enhance + Medium sharpening |
| JPEG output has white patches | Normal — RGBA→JPEG conversion adds white background |
| Very slow on large images | Use Bilinear for speed, or reduce scale factor |

---

## Algorithm Quick Reference

```
Photo / Screenshot   →  Lanczos + Light sharpening
Illustration / Logo  →  Bicubic
Pixel Art / Sprites  →  Nearest Neighbour
Scanned Document     →  Edge Enhance + Denoise
Quick Batch          →  Bilinear
Not sure             →  Lanczos 2× (always a safe choice)
```
