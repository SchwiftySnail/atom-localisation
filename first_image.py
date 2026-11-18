"""Lesson 1: create an image and explore row and column indices."""

from pathlib import Path

import matplotlib

# Save the figure without requiring a separate graphical window.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def make_image():
    """Return a 64-row, 64-column image of floating-point intensities."""
    image = np.zeros((64, 64), dtype=float)

    # Your exercise goes here. Read lessons/01-images-as-arrays.md first.
    # Change individual pixels using image[row, column] = intensity.
    image[20, 40] = 1.0
    image[40,20] = 0.5
    return image

def main():
    image = make_image()
    output_directory = Path(__file__).resolve().parent / "outputs"
    output_directory.mkdir(exist_ok=True)
    output_path = output_directory / "first_image.png"

    figure, axes = plt.subplots(figsize=(6, 5))
    displayed_image = axes.imshow(
        image,
        cmap="gray",
        origin="lower",
        interpolation="nearest",
        vmin=0,
        vmax=1,
    )
    axes.set_xlabel("Column index, x (pixels)")
    axes.set_ylabel("Row index, y (pixels)")
    axes.set_title("An image stored as a NumPy array")
    figure.colorbar(displayed_image, ax=axes, label="Intensity (arbitrary units)")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

    print(f"Image shape: {image.shape}")
    print(f"Non-zero pixels: {np.count_nonzero(image)}")
    print(f"Saved image to: {output_path}")


if __name__ == "__main__":
    main()
