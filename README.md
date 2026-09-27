# VideoSubFinder (Modernized Edition)

A modernized, high-performance fork of VideoSubFinder with hardware-accelerated decoding (D3D11VA for AMD, Intel, NVIDIA), streamlined subtitle naming, integrated AI-based false-positive filtering via DirectML GPU, and automated GitHub Actions CI/CD.

---

## Key Highlights & Improvements

### 1. Modern FFmpeg 9.x Upgrade & D3D11VA Hardware Acceleration
- Upgraded the legacy FFmpeg decoding backend to modern FFmpeg 9.0.2 APIs.
- Integrated Direct3D 11 Video Acceleration (`d3d11va`) for hardware-accelerated video decoding across AMD Radeon, Intel, and NVIDIA GPUs on Windows.
- Implemented high-speed ROI (Region of Interest) NV12-to-BGR color conversion, transferring video frames directly into computer vision memory without full-frame software overhead.
- Achieved ~7.6x realtime extraction speed on 1080p video on AMD Ryzen + Radeon RX hardware.

### 2. Streamlined Subtitle Naming Format
- Output image filenames are standardized for subsequent OCR pipelines (PaddleOCR, RapidOCR, Tesseract, Subtitle Edit, LLM processors):
  - `bot_HH_MM_SS_MS__HH_MM_SS_MS.jpg` (bottom subtitle box)
  - `top_HH_MM_SS_MS__HH_MM_SS_MS.jpg` (top subtitle box)
- Format uses 2-digit hour precision (`00_01_23_456__00_01_26_789.jpg`), clean `.jpg` extension, and removes redundant coordinate and debug suffixes.

### 3. Integrated AI False-Positive Cleanup (`clean_rgb_images.py`)
- Automated detection and removal of non-subtitle images (camera flashes, scene backgrounds, face close-ups, clothing patterns) from the `RGBImages` folder.
- Powered by RapidOCR DBNet neural network text detection with native **DirectML GPU acceleration** (`onnxruntime-directml`) on AMD Radeon GPUs (and CUDA on NVIDIA GPUs).
- Features smart bounding box heuristics (aspect ratio filtering, confidence scoring, minimum size thresholds) that remove scene clutter while preserving 100% of short and single-character subtitles (such as "U.", "Om...", "Thi...").
- Integrated directly into the GUI via the **"Clean RGB Images"** button with interactive options (move to `_trash` vs permanent delete).

### 4. Automated CI/CD (GitHub Actions)
- Continuous integration on `windows-2022` runners with automated toolchain setup (CUDA 12.4, OpenCV 4.7.0, wxWidgets 3.2.1, FFmpeg 9.0.2).
- Automatically packages runtime DLLs, UI bitmaps, localization configs, and Python tools into `VideoSubFinder_x64.zip`.
- Automatically publishes GitHub Releases when pushing version tags (`v*`).

---

## System Requirements

- **Operating System**: Windows 10 / 11 (64-bit).
- **Graphics Card**: AMD Radeon, NVIDIA GeForce, or Intel Iris/Arc GPU with DirectX 11 support.
- **Runtime Dependency**: Microsoft Visual C++ 2022 Redistributable (x64).
- **Python (Optional, for Clean RGB Images tool)**: Python 3.10+ with packages from `requirements.txt`.

---

## Installation & Setup

### Option A: Download Pre-built Release
1. Download the latest `VideoSubFinder_x64.zip` from the **Releases** or **Actions** tab on GitHub.
2. Extract the archive to any directory (e.g. `C:\VideoSubFinder\`).
3. (Optional, to use Clean RGB Images) Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Note for AMD GPU users*: Ensure `onnxruntime-directml` is installed without conflicting CPU `onnxruntime` packages:
   ```bash
   pip uninstall -y onnxruntime
   pip install onnxruntime-directml
   ```

### Option B: Build from Source
See the [Building from Source](#building-from-source) section below.

---

## Usage Guide

### 1. Extracting Subtitles (GUI)
1. Run `VideoSubFinderWXW.exe`.
2. Open your video file via **File -> Open Video**.
3. Set your subtitle bounding boxes:
   - Drag the red box to cover the bottom subtitle area.
   - (Optional) Enable and drag the top box if the video has top captions or sign translations.
4. Click **Run** on the Search panel to begin scanning.
5. Extracted subtitle crops will be saved to the `RGBImages` directory.

### 2. Cleaning False-Positive Images
After extraction finishes:
- **Via GUI**: Click the **Clean RGB Images** button on the Search panel. Select whether to move non-text images into `_trash` or delete them permanently.
- **Via Command Line**:
  ```bash
  # Move non-text images to _trash (recommended)
  python clean_rgb_images.py --action move

  # Delete non-text images permanently
  python clean_rgb_images.py --action delete

  # Run on a custom directory
  python clean_rgb_images.py --dir "D:\Path\To\RGBImages" --action move

  # Enable strict filtering mode for complex anime backgrounds
  python clean_rgb_images.py --strict
  ```

#### CLI Parameters for `clean_rgb_images.py`
| Argument | Default | Description |
|---|---|---|
| `--dir` | `./RGBImages` | Path to directory containing `.jpg` subtitle images. |
| `--action` | `move` | `move` to move trash images to `_trash`, `delete` to remove permanently. |
| `--trash-dir` | `<dir>/_trash` | Target folder for non-text images when using `--action move`. |
| `--min-area` | `500` | Minimum bounding box area in pixels squared. |
| `--min-w` | `35` | Minimum bounding box width in pixels. |
| `--min-h` | `14` | Minimum bounding box height in pixels. |
| `--strict` | `False` | Enable tighter thresholds to filter complex background drawings. |

---

## Building from Source

### Prerequisites
- Visual Studio 2022 (Community / Professional / Enterprise) with C++ Desktop Development.
- CMake 3.13 or newer.
- Dependencies:
  - wxWidgets 3.2.1 x64 (headers, dev, release DLLs)
  - OpenCV 4.7.0 x64
  - FFmpeg 9.0.2 shared x64 (GyanD full shared build)
  - CUDA Toolkit 12.4 (optional, for CUDA acceleration)

### Building via MSBuild
Set the required environment variables and run MSBuild on the solution:
```powershell
$env:WX_WIDGETS_PATH = "C:\wxWidgets-3.2.1"
$env:OPENCV_BUILD_PATH_X64 = "C:\opencv_build"
$env:OPENCV_LIBS_VER = "470"
$env:FFMPEG_PATH_X64 = "C:\ffmpeg"
$env:CUDA_TOOLKIT_PATH = $env:CUDA_PATH
$env:CL = "/DWXUSINGDLL"

msbuild Interfaces\VideoSubFinderWXW\VideoSubFinderWXW.sln `
  /p:Configuration=Release `
  /p:Platform=x64 `
  /m
```

The compiled executable will be placed in `Build\Release_x64\`.

---

## Automated Releases via GitHub Actions

This repository includes a ready-to-use GitHub Actions workflow in `.github/workflows/build.yml`.

To publish a new automated release:
1. Commit your changes:
   ```bash
   git add .
   git commit -m "Release version 1.0.0"
   git push origin main
   ```
2. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions will build the complete project and upload `VideoSubFinder_x64.zip` directly to the new Release on GitHub.

---

## License & Credits

- Original VideoSubFinder by Simeon Kosnitsky: https://sourceforge.net/projects/videosubfinder/
- RapidOCR by SWHL: https://github.com/RapidAI/RapidOCR
- FFmpeg: https://ffmpeg.org/
- OpenCV: https://opencv.org/
- wxWidgets: https://www.wxwidgets.org/
