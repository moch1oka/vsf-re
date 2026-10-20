# VideoSubFinder (Midnight Reverie Edition)

A modernized fork of [VideoSubFinder](https://sourceforge.net/projects/videosubfinder/) with hardware-accelerated decoding (D3D11VA), a second subtitle search box, and AI-based cleanup of false-positive images.

---

## Highlights

### FFmpeg 9.x and D3D11VA hardware decoding
- Decoding backend updated to the FFmpeg 9.x API.
- Direct3D 11 Video Acceleration (`d3d11va`) on AMD, Intel and NVIDIA GPUs on Windows. It is the default `hw_device` in `settings/general.cfg`.
- If the hardware device can't be used (no driver support, unsupported codec, non-Windows OS), the video is opened with CPU decoding automatically.
- Fast NV12 → BGR conversion of only the search region, without converting the full frame.
- Measured ~7.6x realtime on 1080p video (AMD Ryzen + Radeon RX).

### Two subtitle boxes
- Besides the usual bottom box, an optional top box can be enabled (checkbox on the Search panel, or `-u2b` on the command line) for top captions and sign translations.
- The search runs in two passes (`[1/2]` bottom, `[2/2]` top). Images from each box are saved with a `bot_` or `top_` prefix.
- When subtitles are created, both boxes are merged in time order. Each box is treated as its own track, so a top caption never shortens a bottom subtitle.

### AI false-positive cleanup (`clean_rgb_images.py`)
- Removes images without subtitles (camera flashes, backgrounds, close-ups, clothing patterns) from `RGBImages`.
- Uses RapidOCR DBNet text detection, with GPU acceleration through DirectML (`onnxruntime-directml`, AMD/Intel/NVIDIA) or CUDA when available.
- Box heuristics (size, aspect ratio, confidence) are tuned to keep very short lines such as "Ừ." or "Ờ...".
- Available from the GUI (**Clean RGB Images** button) and from the command line.

---

## Image file names

Images in `RGBImages` are named:

```
<box>_<start>__<end>_<geometry>.jpg
```

| Part | Example | Meaning |
|---|---|---|
| `<box>` | `bot` / `top` | Subtitle box the image comes from. |
| `<start>`, `<end>` | `00_01_23_456` | Time as `HH_MM_SS_mmm` (2-digit hour). |
| `<geometry>` | `0000009601920012019201080` | 25 digits: line index (1), then `xmin`, `ymin`, `w`, `h` of the crop and `W`, `H` of the video frame (4 digits each). |

Example: `bot_00_01_23_456__00_01_26_789_0000009601920012019201080.jpg`

The geometry suffix is required by **Create Cleared TXT Images** and **Join Images**: they use it to recover the crop position and the original frame size. External OCR tools can simply read the times from the part before the last `_`.

---

## Installation

### Pre-built release
1. Download `VideoSubFinder_x64.zip` from the **Releases** (or **Actions**) tab.
2. Extract it anywhere, e.g. `C:\VideoSubFinder\`.
3. Optional, for **Clean RGB Images**: install Python 3 and the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   On AMD GPUs make sure only the DirectML build of ONNX Runtime is installed:
   ```bash
   pip uninstall -y onnxruntime
   pip install onnxruntime-directml
   ```

### Build from source
See [Building from source](#building-from-source).

---

## Usage

### 1. Extract subtitle images (GUI)
1. Run `VideoSubFinderWXW.exe`.
2. Open the video with **File → Open Video (FFMPEG)**.
3. Place the red box over the bottom subtitle area. Optionally enable the top box and place it over top captions.
4. Click **Run** on the Search panel.
5. Images are saved to `RGBImages`.

### 2. Remove false positives
**From the GUI:** click **Clean RGB Images** on the Search panel and choose:
- **Yes**: move non-text images to `RGBImages/_trash` (recommended, reversible).
- **No**: delete them permanently.

The script is looked up next to `VideoSubFinderWXW.exe`, then in the current directory. `python` from `PATH` is used; set the `VSF_PYTHON` environment variable to use a specific interpreter, e.g. `C:\Python312\python.exe`.

`_trash` is ignored by all OCR steps and is removed by **Clear Folders**.

**From the command line:**
```bash
# Move non-text images to RGBImages/_trash (run from the VideoSubFinder folder)
python clean_rgb_images.py --action move

# Custom folder, permanent delete
python clean_rgb_images.py --dir "D:\Path\To\RGBImages" --action delete

# Stricter thresholds for busy backgrounds
python clean_rgb_images.py --strict
```

| Argument | Default | Description |
|---|---|---|
| `--dir` | `RGBImages` | Image folder (`.jpg`, `.jpeg`, `.png`, `.bmp`), relative to the current directory. |
| `--action` | `move` | `move` to `_trash`, or `delete` permanently. |
| `--trash-dir` | `<dir>/_trash` | Destination for `move`. |
| `--min-area` | `500` | Minimum text box area (px²). |
| `--min-w` | `35` | Minimum text box width (px). |
| `--min-h` | `14` | Minimum text box height (px). |
| `--strict` | off | Tighter thresholds. |

The script exits with code `1` if the folder doesn't exist.

### 3. Create subtitles
Continue on the OCR panel as in upstream VideoSubFinder (**Create Cleared TXT Images**, **Join Images**, **Create Sub From TXT Results**, …).

### Command line
The upstream options are supported, plus:

| Option | Description |
|---|---|
| `-u2b`, `--use_two_video_boxes` | Also search the top box. |
| `-te2`, `-be2` | Top / bottom edge of the top box, as a fraction of the frame height (like `-te` / `-be`). |

Run `VideoSubFinderWXW.exe -h` for the full list. A command-line run exits with code `1` if the input video can't be opened.

---

## Building from source

### Prerequisites
- Visual Studio 2022 with *Desktop development with C++*.
- wxWidgets 3.2.1 x64 (headers, dev libs, release DLLs).
- OpenCV 4.7.0 x64.
- FFmpeg 9.x shared x64 (e.g. the GyanD full shared build).
- CUDA Toolkit 12.4 (for the CUDA build).

### MSBuild
```powershell
$env:WX_WIDGETS_PATH = "C:\wxWidgets-3.2.1"
$env:OPENCV_BUILD_PATH_X64 = "C:\opencv_build"
$env:OPENCV_LIBS_VER = "470"
$env:FFMPEG_PATH_X64 = "C:\ffmpeg"
$env:CUDA_TOOLKIT_PATH = $env:CUDA_PATH
$env:CL = "/DWXUSINGDLL"

msbuild Interfaces\VideoSubFinderWXW\VideoSubFinderWXW.sln /p:Configuration=Release /p:Platform=x64 /m
```

The executable is written to `Build\Release_x64\`.

### CMake
`CMakeLists.txt` reads the same environment variables. Cache values passed with `-D` (e.g. `-DOpenCV_LIBS=opencv_world480.lib`) take precedence. Use `-DUSE_CUDA=OFF` to build without CUDA.

---

## Releases (GitHub Actions)

`.github/workflows/build.yml` builds every push and pull request and uploads `VideoSubFinder_x64.zip` as a build artifact. Pushing a `v*` tag also publishes a GitHub Release:

```bash
git tag v1.0.1
git push origin v1.0.1
```

---

## Credits

- VideoSubFinder by Simeon Kosnitsky: https://sourceforge.net/projects/videosubfinder/
- RapidOCR: https://github.com/RapidAI/RapidOCR
- FFmpeg: https://ffmpeg.org/
- OpenCV: https://opencv.org/
- wxWidgets: https://www.wxwidgets.org/
