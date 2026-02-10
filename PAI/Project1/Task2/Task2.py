"""
Part 2: Image Processing & Enhancement
========================================
Multi-Modal Document Intelligence System

This module applies various image processing techniques to images
extracted from the PDF, including:
- Basic transformations (grayscale, resize, rotate)
- Image enhancement (histogram equalization, blur, edge detection)
- Advanced processing (morphological operations, thumbnails)
- Side-by-side comparison image generation

Required Libraries: OpenCV (cv2), Pillow (PIL), NumPy
"""

import os
import sys
import time
import logging
from typing import List, Dict, Tuple, Optional

try:
    import cv2
except ImportError:
    print("Error: OpenCV is required. Install with: pip install opencv-python")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: NumPy is required. Install with: pip install numpy")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

RESIZE_TARGET = (800, 600)       # Target dimensions for resizing
THUMBNAIL_SIZE = (150, 150)      # Thumbnail dimensions
ROTATION_ANGLE = 45              # Rotation angle in degrees
GAUSSIAN_KERNEL = (5, 5)         # Gaussian blur kernel size
CANNY_THRESHOLD_LOW = 50         # Canny edge detection low threshold
CANNY_THRESHOLD_HIGH = 150       # Canny edge detection high threshold
MORPH_KERNEL_SIZE = (5, 5)       # Morphological operation kernel size


# ============================================================
# Basic Transformations
# ============================================================

def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert a color image to grayscale.

    Args:
        image (np.ndarray): Input color image (BGR format).

    Returns:
        np.ndarray: Grayscale version of the image.

    Raises:
        ValueError: If the input image is None or empty.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    # If already grayscale, return as-is
    if len(image.shape) == 2:
        logger.info("  Image is already grayscale.")
        return image.copy()

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    logger.info("  Converted to grayscale.")
    return grayscale


def resize_image(
    image: np.ndarray,
    target_size: Tuple[int, int] = RESIZE_TARGET,
    maintain_aspect: bool = True
) -> np.ndarray:
    """
    Resize an image to the target dimensions.

    If maintain_aspect is True, the image is resized to fit within
    the target dimensions while preserving the aspect ratio, with
    padding added to reach the exact target size.

    Args:
        image (np.ndarray): Input image.
        target_size (Tuple[int, int]): Target (width, height) in pixels.
        maintain_aspect (bool): Whether to maintain the aspect ratio.

    Returns:
        np.ndarray: Resized image.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    target_w, target_h = target_size

    if not maintain_aspect:
        # Simple resize without maintaining aspect ratio
        resized = cv2.resize(
            image, (target_w, target_h),
            interpolation=cv2.INTER_AREA
        )
        logger.info(f"  Resized to {target_w}x{target_h} (no aspect ratio).")
        return resized

    # Calculate aspect-ratio-preserving dimensions
    h, w = image.shape[:2]
    aspect_ratio = w / h

    if aspect_ratio > (target_w / target_h):
        # Width is the limiting factor
        new_w = target_w
        new_h = int(target_w / aspect_ratio)
    else:
        # Height is the limiting factor
        new_h = target_h
        new_w = int(target_h * aspect_ratio)

    # Resize the image
    resized = cv2.resize(
        image, (new_w, new_h),
        interpolation=cv2.INTER_AREA
    )

    # Create a canvas of the target size and center the resized image
    if len(image.shape) == 3:
        canvas = np.zeros((target_h, target_w, image.shape[2]), dtype=np.uint8)
    else:
        canvas = np.zeros((target_h, target_w), dtype=np.uint8)

    # Calculate offset to center the image
    y_offset = (target_h - new_h) // 2
    x_offset = (target_w - new_w) // 2

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    logger.info(
        f"  Resized to {target_w}x{target_h} "
        f"(aspect ratio maintained, original: {w}x{h})."
    )
    return canvas


def rotate_image(
    image: np.ndarray,
    angle: float = ROTATION_ANGLE
) -> np.ndarray:
    """
    Rotate an image by the specified angle around its center.

    The output image is large enough to contain the entire
    rotated image without cropping.

    Args:
        image (np.ndarray): Input image.
        angle (float): Rotation angle in degrees (counterclockwise).

    Returns:
        np.ndarray: Rotated image.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    # Get the rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Calculate the new bounding box size to avoid cropping
    cos_val = abs(rotation_matrix[0, 0])
    sin_val = abs(rotation_matrix[0, 1])
    new_w = int(h * sin_val + w * cos_val)
    new_h = int(h * cos_val + w * sin_val)

    # Adjust the rotation matrix for the new center
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]

    # Apply the rotation
    rotated = cv2.warpAffine(
        image, rotation_matrix, (new_w, new_h),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    logger.info(f"  Rotated by {angle} degrees.")
    return rotated


# ============================================================
# Image Enhancement
# ============================================================

def apply_histogram_equalization(image: np.ndarray) -> np.ndarray:
    """
    Apply histogram equalization to improve image contrast.

    For color images, the equalization is applied to the V channel
    in HSV color space to preserve color information.

    Args:
        image (np.ndarray): Input image (grayscale or BGR).

    Returns:
        np.ndarray: Contrast-enhanced image.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    if len(image.shape) == 2:
        # Grayscale image - apply directly
        equalized = cv2.equalizeHist(image)
    else:
        # Color image - convert to HSV and equalize V channel
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v_equalized = cv2.equalizeHist(v)
        hsv_equalized = cv2.merge([h, s, v_equalized])
        equalized = cv2.cvtColor(hsv_equalized, cv2.COLOR_HSV2BGR)

    logger.info("  Applied histogram equalization.")
    return equalized


def apply_gaussian_blur(
    image: np.ndarray,
    kernel_size: Tuple[int, int] = GAUSSIAN_KERNEL
) -> np.ndarray:
    """
    Apply Gaussian blur to smooth the image.

    Args:
        image (np.ndarray): Input image.
        kernel_size (Tuple[int, int]): Size of the Gaussian kernel.
            Both values must be positive and odd.

    Returns:
        np.ndarray: Blurred image.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    # Ensure kernel size values are odd
    kw = kernel_size[0] if kernel_size[0] % 2 == 1 else kernel_size[0] + 1
    kh = kernel_size[1] if kernel_size[1] % 2 == 1 else kernel_size[1] + 1

    blurred = cv2.GaussianBlur(image, (kw, kh), 0)
    logger.info(f"  Applied Gaussian blur with kernel {kw}x{kh}.")
    return blurred


def detect_edges_canny(
    image: np.ndarray,
    low_threshold: int = CANNY_THRESHOLD_LOW,
    high_threshold: int = CANNY_THRESHOLD_HIGH
) -> np.ndarray:
    """
    Detect edges in the image using the Canny edge detection algorithm.

    The input image is first converted to grayscale if it is a color image.

    Args:
        image (np.ndarray): Input image.
        low_threshold (int): Lower threshold for hysteresis.
        high_threshold (int): Upper threshold for hysteresis.

    Returns:
        np.ndarray: Binary edge map.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Apply slight blur before edge detection to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    edges = cv2.Canny(blurred, low_threshold, high_threshold)
    logger.info(
        f"  Detected edges (Canny: low={low_threshold}, "
        f"high={high_threshold})."
    )
    return edges


# ============================================================
# Advanced Processing
# ============================================================

def apply_morphological_operations(
    image: np.ndarray,
    kernel_size: Tuple[int, int] = MORPH_KERNEL_SIZE
) -> Dict[str, np.ndarray]:
    """
    Apply morphological operations to the image.

    Performs erosion, dilation, opening, and closing operations.
    For color images, operations are applied to a grayscale version.

    Args:
        image (np.ndarray): Input image.
        kernel_size (Tuple[int, int]): Size of the structuring element.

    Returns:
        Dict[str, np.ndarray]: Dictionary mapping operation names to
            their resulting images. Keys: 'erosion', 'dilation',
            'opening', 'closing'.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    # Convert to grayscale for morphological operations
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Create structuring element (kernel)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)

    # Apply morphological operations
    results = {
        "erosion": cv2.erode(gray, kernel, iterations=1),
        "dilation": cv2.dilate(gray, kernel, iterations=1),
        "opening": cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel),
        "closing": cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel),
    }

    logger.info(
        f"  Applied morphological operations "
        f"(kernel: {kernel_size[0]}x{kernel_size[1]})."
    )
    return results


def create_thumbnail(
    image: np.ndarray,
    size: Tuple[int, int] = THUMBNAIL_SIZE
) -> np.ndarray:
    """
    Create a thumbnail version of the image.

    The thumbnail maintains the aspect ratio and is padded to
    fit exactly within the specified size.

    Args:
        image (np.ndarray): Input image.
        size (Tuple[int, int]): Thumbnail dimensions (width, height).

    Returns:
        np.ndarray: Thumbnail image.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is None or empty.")

    thumbnail = resize_image(image, size, maintain_aspect=True)
    logger.info(f"  Created thumbnail ({size[0]}x{size[1]}).")
    return thumbnail


# ============================================================
# Side-by-Side Comparison
# ============================================================

def create_comparison_image(
    original: np.ndarray,
    processed_versions: Dict[str, np.ndarray],
    output_path: str,
    max_cols: int = 3
) -> str:
    """
    Create a side-by-side comparison image showing original
    and all processed versions.

    Images are arranged in a grid layout with labels beneath
    each version. All images are resized to a uniform size
    for consistent display.

    Args:
        original (np.ndarray): Original input image.
        processed_versions (Dict[str, np.ndarray]): Dictionary mapping
            version names to processed images.
        output_path (str): Path to save the comparison image.
        max_cols (int): Maximum number of columns in the grid.

    Returns:
        str: Path to the saved comparison image.
    """
    # Uniform cell size for the grid
    cell_w, cell_h = 300, 250
    label_height = 30

    # Prepare all images with labels
    all_images = {"Original": original}
    all_images.update(processed_versions)

    num_images = len(all_images)
    num_cols = min(num_images, max_cols)
    num_rows = (num_images + num_cols - 1) // num_cols

    # Total canvas size
    canvas_w = num_cols * cell_w
    canvas_h = num_rows * (cell_h + label_height)

    # Create canvas using Pillow for better text rendering
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Try to load a font; fall back to default if unavailable
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except (IOError, OSError):
        font = ImageFont.load_default()

    for idx, (label, img) in enumerate(all_images.items()):
        row = idx // num_cols
        col = idx % num_cols

        x_pos = col * cell_w
        y_pos = row * (cell_h + label_height)

        # Convert image to RGB for Pillow compatibility
        if img is None:
            continue

        if len(img.shape) == 2:
            # Grayscale -> RGB for display
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Resize to fit cell
        pil_img = Image.fromarray(img_rgb)
        pil_img.thumbnail((cell_w - 10, cell_h - 10), Image.LANCZOS)

        # Calculate position to center in cell
        paste_x = x_pos + (cell_w - pil_img.width) // 2
        paste_y = y_pos + (cell_h - pil_img.height) // 2

        canvas.paste(pil_img, (paste_x, paste_y))

        # Draw label
        label_y = y_pos + cell_h
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        label_x = x_pos + (cell_w - text_w) // 2
        draw.text((label_x, label_y + 5), label, fill=(0, 0, 0), font=font)

    # Save the comparison image
    canvas.save(output_path, "PNG")
    logger.info(f"  Comparison image saved: {output_path}")
    return output_path


# ============================================================
# Full Image Processing Pipeline
# ============================================================

def process_single_image(
    image_path: str,
    output_dir: str
) -> Dict[str, str]:
    """
    Apply the complete processing pipeline to a single image.

    Performs all required transformations and saves each version
    with a descriptive filename.

    Args:
        image_path (str): Path to the input image.
        output_dir (str): Directory for saving processed images.

    Returns:
        Dict[str, str]: Dictionary mapping operation names to
            output file paths.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load the original image
    original = cv2.imread(image_path)
    if original is None:
        raise ValueError(f"Could not load image: {image_path}")

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    output_files = {}

    # --- Basic Transformations ---
    logger.info(f"Processing: {base_name}")

    # 1. Grayscale
    grayscale = convert_to_grayscale(original)
    gray_path = os.path.join(output_dir, f"{base_name}_grayscale.png")
    cv2.imwrite(gray_path, grayscale)
    output_files["Grayscale"] = gray_path

    # 2. Resize (maintaining aspect ratio)
    resized = resize_image(original, RESIZE_TARGET, maintain_aspect=True)
    resized_path = os.path.join(output_dir, f"{base_name}_resized_800x600.png")
    cv2.imwrite(resized_path, resized)
    output_files["Resized 800x600"] = resized_path

    # 3. Rotate 45 degrees
    rotated = rotate_image(original, ROTATION_ANGLE)
    rotated_path = os.path.join(output_dir, f"{base_name}_rotated_45deg.png")
    cv2.imwrite(rotated_path, rotated)
    output_files["Rotated 45°"] = rotated_path

    # --- Image Enhancement ---

    # 4. Histogram equalization
    equalized = apply_histogram_equalization(original)
    eq_path = os.path.join(output_dir, f"{base_name}_histogram_eq.png")
    cv2.imwrite(eq_path, equalized)
    output_files["Histogram Eq."] = eq_path

    # 5. Gaussian blur
    blurred = apply_gaussian_blur(original, GAUSSIAN_KERNEL)
    blur_path = os.path.join(output_dir, f"{base_name}_gaussian_blur.png")
    cv2.imwrite(blur_path, blurred)
    output_files["Gaussian Blur"] = blur_path

    # 6. Canny edge detection
    edges = detect_edges_canny(original)
    edges_path = os.path.join(output_dir, f"{base_name}_canny_edges.png")
    cv2.imwrite(edges_path, edges)
    output_files["Canny Edges"] = edges_path

    # --- Advanced Processing ---

    # 7. Morphological operations
    morph_results = apply_morphological_operations(original)
    for op_name, morph_img in morph_results.items():
        morph_path = os.path.join(
            output_dir, f"{base_name}_morph_{op_name}.png"
        )
        cv2.imwrite(morph_path, morph_img)
        output_files[f"Morph: {op_name.capitalize()}"] = morph_path

    # 8. Thumbnail
    thumbnail = create_thumbnail(original, THUMBNAIL_SIZE)
    thumb_path = os.path.join(output_dir, f"{base_name}_thumbnail_150x150.png")
    cv2.imwrite(thumb_path, thumbnail)
    output_files["Thumbnail"] = thumb_path

    # --- Comparison Image ---
    comparison_versions = {
        "Grayscale": grayscale,
        "Resized": resized,
        "Rotated 45°": rotated,
        "Hist. Equalized": equalized,
        "Gaussian Blur": blurred,
        "Canny Edges": edges,
        "Morph: Closing": morph_results["closing"],
        "Thumbnail": thumbnail,
    }

    comparison_path = os.path.join(
        output_dir, f"{base_name}_comparison.png"
    )
    create_comparison_image(original, comparison_versions, comparison_path)
    output_files["Comparison"] = comparison_path

    return output_files


# ============================================================
# Batch Processing
# ============================================================

def process_all_images(
    image_paths: List[str],
    output_dir: str
) -> Dict[str, Dict[str, str]]:
    """
    Process all extracted images through the complete pipeline.

    Args:
        image_paths (List[str]): List of paths to images to process.
        output_dir (str): Root output directory for processed images.

    Returns:
        Dict[str, Dict[str, str]]: Nested dictionary mapping each
            input image name to its processing results.
    """
    start_time = time.time()

    print("\n" + "=" * 60)
    print("  PART 2: IMAGE PROCESSING & ENHANCEMENT")
    print("=" * 60)

    processed_dir = os.path.join(output_dir, "processed_images")
    os.makedirs(processed_dir, exist_ok=True)

    all_results = {}
    successful = 0
    failed = 0

    for img_path in tqdm(image_paths, desc="Processing images"):
        img_name = os.path.basename(img_path)
        try:
            # Create subdirectory for each image's processed versions
            img_output_dir = os.path.join(
                processed_dir,
                os.path.splitext(img_name)[0]
            )
            results = process_single_image(img_path, img_output_dir)
            all_results[img_name] = results
            successful += 1
        except Exception as e:
            logger.error(f"Failed to process {img_name}: {e}")
            all_results[img_name] = {"error": str(e)}
            failed += 1

    total_time = time.time() - start_time

    print(f"\n  Image Processing Complete!")
    print(f"  Successfully processed: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Time elapsed: {total_time:.2f}s")

    return all_results


# ============================================================
# Script Entry Point
# ============================================================

if __name__ == "__main__":
    """
    Run Part 2 as a standalone script.
    
    Usage:
        python image_processing.py <image_path_or_directory> [output_directory]
    
    Examples:
        python image_processing.py ./extracted_images/
        python image_processing.py image.png ./output
    """
    if len(sys.argv) < 2:
        print(
            "Usage: python image_processing.py "
            "<image_path_or_directory> [output_directory]"
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "./output"

    # Collect image paths
    if os.path.isdir(input_path):
        # Process all images in the directory
        valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
        image_files = [
            os.path.join(input_path, f)
            for f in sorted(os.listdir(input_path))
            if os.path.splitext(f)[1].lower() in valid_extensions
        ]
    elif os.path.isfile(input_path):
        image_files = [input_path]
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    if not image_files:
        print("No valid image files found.")
        sys.exit(1)

    print(f"Found {len(image_files)} image(s) to process.")

    try:
        results = process_all_images(image_files, output_directory)
        print("\nPart 2 completed successfully!")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
