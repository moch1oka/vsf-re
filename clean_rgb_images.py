"""
Script lọc và dọn dẹp ảnh rác (không có phụ đề) trong thư mục RGBImages
sử dụng mô hình Text Detection (DBNet) siêu nhẹ từ RapidOCR.
"""

import argparse
import glob
import os
import shutil
import sys
import time
import cv2
from rapidocr_onnxruntime import RapidOCR
from tqdm import tqdm


def filter_images(img_dir, action="move", trash_dir=None, min_box_area=500, min_w=35, min_h=14, min_score=0.50, min_small_score=0.56, strict=False):
    if not os.path.isdir(img_dir):
        print(f"Error: Thu muc '{img_dir}' khong ton tai.")
        return

    pattern = os.path.join(img_dir, "*.jpg")
    files = glob.glob(pattern)
    total_files = len(files)
    if total_files == 0:
        print(f"Khong tim thay anh .jpg nao trong '{img_dir}'.")
        return

    if trash_dir is None:
        trash_dir = os.path.join(img_dir, "_trash")

    if action == "move":
        os.makedirs(trash_dir, exist_ok=True)

    if strict:
        min_box_area = max(min_box_area, 700)
        min_w = max(min_w, 40)
        min_h = max(min_h, 15)
        min_small_score = max(min_small_score, 0.58)

    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        use_dml = "DmlExecutionProvider" in available_providers
        use_cuda = "CUDAExecutionProvider" in available_providers
    except Exception:
        use_dml = False
        use_cuda = False

    device_str = "GPU (DirectML)" if use_dml else ("GPU (CUDA)" if use_cuda else "CPU")
    mode_str = "Strict" if strict else "Standard"
    print(f"Dang khoi tao mo hinh Text Detector tren {device_str} [Che do: {mode_str}]...")
    engine = RapidOCR(
        det_limit_type="max",
        det_limit_side_len=960,
        det_use_dml=use_dml,
        det_use_cuda=use_cuda,
    )
    actual_providers = engine.text_det.infer.session.get_providers()
    print(f"ONNX Runtime Execution Providers: {actual_providers}")

    # Warmup
    dummy = cv2.imread(files[0])
    if dummy is not None:
        dummy_shape = dummy.shape[:2]
        dummy_prep = engine.text_det.get_preprocess(max(dummy_shape))
        dummy_preds = engine.text_det.infer(dummy_prep(dummy))[0]
        engine.text_det.postprocess_op(dummy_preds, dummy_shape)

    print(f"Dang quet {total_files} anh trong '{img_dir}'...")
    start_time = time.time()

    valid_count = 0
    garbage_count = 0
    garbage_list = []

    is_tty = sys.stdout.isatty()
    pbar = tqdm(files, desc="Loc anh phu de", unit="anh") if is_tty else files

    for file_path in pbar:
        img = cv2.imread(file_path)
        if img is None:
            continue

        ori_shape = img.shape[:2]
        prep = engine.text_det.get_preprocess(max(ori_shape))
        preds = engine.text_det.infer(prep(img))[0]
        boxes, scores = engine.text_det.postprocess_op(preds, ori_shape)

        has_text = False
        if len(boxes) > 0:
            for b, s in zip(boxes, scores):
                if s < min_score:
                    continue

                xs = [pt[0] for pt in b]
                ys = [pt[1] for pt in b]
                w = max(xs) - min(xs)
                h = max(ys) - min(ys)
                area = w * h
                ar = w / max(h, 1)

                # 1. Kich thuoc hinh hoc toi thieu
                if area < min_box_area or w < min_w or h < min_h:
                    continue

                # 2. Cac vat the vuong hoac tron (hoa cai toc, icon, nut: w/h tu 0.75 den 1.25)
                if 0.75 <= ar <= 1.25 and area < 5000 and s < 0.70:
                    continue

                # 3. Hop chu nho (< 2000px^2) can do tin cay cao hon de tranh vet nhieu
                if area < 2000 and s < min_small_score:
                    continue

                has_text = True
                break

        if has_text:
            valid_count += 1
        else:
            garbage_count += 1
            filename = os.path.basename(file_path)
            garbage_list.append(filename)
            if action == "move":
                shutil.move(file_path, os.path.join(trash_dir, filename))
            elif action == "delete":
                os.remove(file_path)

    elapsed = time.time() - start_time
    fps = total_files / elapsed if elapsed > 0 else 0

    print("\n" + "=" * 50)
    print(f"Tong so anh da quet:   {total_files}")
    print(f"Anh co phu de hop le:  {valid_count}")
    print(f"Anh rac da loai bo:    {garbage_count}")
    print(f"Thoi gian thuc hien:   {elapsed:.2f}s ({fps:.1f} anh/giay)")
    if action == "move":
        print(f"Cac anh rac da duoc chuyen vao: {trash_dir}")
    elif action == "delete":
        print(f"Cac anh rac da duoc xoa vinh vien.")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Don anh rac khong co chu trong RGBImages cua VideoSubFinder")
    parser.add_argument("--dir", default=r"F:\VideoSubFinder\Release_AMD\VideoSubFinder\RGBImages",
                        help="Duong dan den thu muc RGBImages")
    parser.add_argument("--action", choices=["move", "delete"], default="move",
                        help="'move' de chuyen vao thu muc _trash, 'delete' de xoa han (mac dinh: move)")
    parser.add_argument("--trash-dir", default=None,
                        help="Thu muc chua anh rac neu dung action='move'")
    parser.add_argument("--min-area", type=int, default=500,
                        help="Dien tich box toi thieu (pixel^2, mac dinh: 500)")
    parser.add_argument("--min-w", type=int, default=35,
                        help="Chieu rong box toi thieu (pixel, mac dinh: 35)")
    parser.add_argument("--min-h", type=int, default=14,
                        help="Chieu cao box toi thieu (pixel, mac dinh: 14)")
    parser.add_argument("--strict", action="store_true",
                        help="Bat che do siet chat nang cao de loai bo them cac vat the canh vat")
    args = parser.parse_args()

    filter_images(
        args.dir,
        action=args.action,
        trash_dir=args.trash_dir,
        min_box_area=args.min_area,
        min_w=args.min_w,
        min_h=args.min_h,
        strict=args.strict,
    )


if __name__ == "__main__":
    main()
