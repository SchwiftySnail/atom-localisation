# Lesson 1: an image is an array

By the end of this lesson, you should be able to place a bright pixel at a chosen position and explain the row and column indices you used.

## Before running the code

The starter contains:

```python
image = np.zeros((64, 64), dtype=float)
```

NumPy stores numerical arrays. This line creates an array with 64 rows and 64 columns, initially filled with zeros. Each number represents a pixel's intensity. Floating-point numbers let us use fractional intensities later.

Indices begin at zero, so valid row and column indices here run from 0 to 63. Access a single value using:

```python
image[row, column]
```

For an image, we will describe horizontal position as x and vertical position as y. NumPy indexing puts the row first, so the corresponding order is `image[y, x]`.

The script uses `origin="lower"` when displaying the array. This places row zero at the bottom. Other image viewers may put row zero at the top, so check this convention whenever you work with new images.

Predict where this example would appear in our figure before trying it:

```python
image[10, 50] = 1.0
```

Would it be near the top or bottom? Near the left or right? Write down your prediction.

## Run the starter

From the project folder:

```sh
python3 first_image.py
```

Open `outputs/first_image.png`. The initial image should be black and the terminal should report zero non-zero pixels.

In this figure, 0 is black and 1 is white. The plotting limits are fixed so that a pixel with intensity 0.5 remains visually distinct from one with intensity 1, even when you change the other values.

## Your task

Edit only `make_image()` in `first_image.py` for now. Add your code between the array creation and `return image`.

1. Place a pixel of intensity 1.0 at horizontal position x = 40 and vertical position y = 20.
2. Place a second pixel of intensity 0.5 at x = 20 and y = 40.
3. Run the script and compare the image with your prediction. It should report two non-zero pixels.

Optional exploration: use an array slice to make a short horizontal line somewhere else. Explain which index you held fixed.

## Explain the result

Add your answers to `research_notes.md`:

- Which index controls horizontal position?
- What would happen if you swapped the indices of the first pixel?
- Would you expect a real image of one atom to occupy exactly one pixel? Why?

Bring back the two lines you added and your answers. If something fails, share the exact error message. We will use this result to build a bright spot that spreads across several pixels in lesson 2.
