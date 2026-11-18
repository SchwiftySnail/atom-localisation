# How the project works

The question is: how does noise change our estimate of a bright spot's position?

The script supplies a known answer, generates a noisy image, measures it without revealing the answer to the position estimators, and compares their estimates with the answer. The result is a controlled numerical experiment.

This Gaussian spot is a teaching model for localisation. It is not a full electron-microscopy simulation and does not reproduce how every atomic image forms.

## 1. From your two pixels to an image model

In your first exercise, `image[20, 40] = 1.0` changed one array entry. A Gaussian assigns an intensity to every pixel according to its distance from a centre:

$$
I(x,y)=b+A\exp\left[-\frac{(x-x_0)^2+(y-y_0)^2}{2\sigma^2}\right].
$$

Here x0 and y0 are the centre coordinates, in pixels. A is the height above a uniform background b, both in arbitrary intensity units. Sigma is the spot width in pixels.

At the centre the exponent is zero, so the continuous model has intensity b + A. At a distance sigma from the centre, the height above background is A times exp(-1/2), approximately 0.607A. A larger sigma spreads the signal further across the image.

Our code samples this formula at pixel centres. For a centre such as (16.35, 15.65), no pixel lies exactly at the centre. That is intentional: a useful estimator should handle an atom whose image falls between pixel centres.

In `model.py`, `np.indices(shape)` supplies coordinate arrays in row, column order. We unpack them as `y, x`. NumPy then evaluates the formula over the arrays without a Python loop for every pixel. This is called vectorisation.

Prediction: if sigma doubles while A remains fixed, does the total signal above background stay constant? In an unbounded continuous plane, its integral is 2πAσ², so it increases fourfold. Our finite sampled image approximates that result when the spot is well contained. Keep that change in total signal in mind when comparing widths.

## 2. Add noise with a recorded seed

For Gaussian noise, each pixel receives an independent random value with mean zero. Its standard deviation is the configured noise level multiplied by A. We retain negative measured values; clipping them would change the noise distribution.

For optional Poisson noise, a pixel's count is sampled with mean equal to its clean intensity multiplied by the count scale. The count is divided by that scale afterwards. If the clean intensity is I and the count scale is c, the rescaled measurement has mean I and variance I/c. A higher c therefore reduces relative noise.

A seed lets us reproduce a sequence of random draws in the recorded software environment. Each scenario has its own stream. All four estimators see the same observed image within each trial, so the comparison is paired. The illustrative image and bootstrap use separate streams.

Question: why would comparing one method on an unusually noisy image and another on an unusually clean image be misleading?

## 3. Estimate the centre in four ways

### Brightest pixel

Find the maximum array entry and convert its row and column to (x, y). It is simple and fast, but noise can move the maximum. Its answer is restricted to integer coordinates.

For the noise-free centre (16.35, 15.65), the nearest pixel is (16, 16). Its radial error is sqrt(0.35² + 0.35²), approximately 0.495 pixels. That error exists before any noise is added.

### Smoothed brightest pixel

Apply a Gaussian filter of fixed width, then find the brightest pixel. Averaging neighbouring values can reduce independent noise, but also changes the signal. The filter reflects values at the image boundary. Its selected position remains an integer pixel.

The smoothing width is a chosen analysis parameter. It is not taken from the true spot width, and we do not tune it using the test results.

### Full-frame clipped centroid

Subtract the known background and set negative weights to zero:

$$
w_{ij}=\max(I_{ij}-b,0).
$$

Then calculate:

$$
\hat{x}=\frac{\sum_{ij}x_{ij}w_{ij}}{\sum_{ij}w_{ij}},\qquad
\hat{y}=\frac{\sum_{ij}y_{ij}w_{ij}}{\sum_{ij}w_{ij}}.
$$

This can return fractional coordinates. However, clipping removes negative noise while retaining positive noise throughout the frame. Those extra weights can pull an off-centre spot's estimate towards the frame centre. A small fixed window or a different treatment of background could give different results.

This baseline is unusually well informed about background because it receives the true simulated b. Real measurements would need an estimate of b. It still does not receive the true centre.

Question: could an estimator look good for an atom exactly at the frame centre simply because its bias also points towards that centre?

### Gaussian fit

Choose the Gaussian parameters that minimise the sum of squared differences between model and observed pixel intensities. SciPy performs the optimisation. We fit amplitude, x, y, sigma and background; none is fixed at its true value.

A smoothed maximum supplies a starting centre. The initial width is an arbitrary two pixels, reduced if needed for a small image. Bounds require a non-negative amplitude, a centre within the frame, and a width between 0.3 pixels and one third of the shorter image dimension. Background is unconstrained. A fit that does not converge or reaches a parameter bound is recorded as a failure.

The code supplies derivatives of the residuals, called a Jacobian, to help the optimiser. You can understand the experiment before learning to derive these derivatives.

The fitted model matches the generating model exactly. That is a favourable test for fitting. Ordinary least squares also assumes a different noise structure from Poisson counting; a Poisson likelihood would be a useful extension.

## 4. Repeat the experiment

One image shows one random outcome. We repeat each condition many times, changing the noise realisation while keeping the true spot fixed. We vary width, noise level and centre position across conditions.

For every successful estimate, define dx = estimated x - true x and dy = estimated y - true y. The radial error is sqrt(dx² + dy²). The root mean square position error is:

$$
\mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_{k=1}^{N}(dx_k^2+dy_k^2)}.
$$

This is not the same as mean radial error. For two radial errors of 0 and 5 pixels, the mean is 2.5 pixels but RMSE is sqrt(12.5), approximately 3.536 pixels. RMSE gives large errors more influence.

The bias vector is (mean dx, mean dy). Scatter around that vector measures variation between trials. A tightly clustered but displaced set of estimates is repeatable and biased.

We resample successful trials with replacement to form a percentile bootstrap interval for RMSE. This interval describes the simulation's finite sample uncertainty. It is not an uncertainty interval for one estimated position or proof that one method is better than another. A method-to-method significance assessment should retain the trial pairing when resampling differences.

Failures stay in `trials.csv` and contribute to `failure_rate`. Their missing errors are not replaced with zero. Reported RMSE is conditional on success, which can flatter a method that fails frequently.

## 5. Read the code in this order

1. `first_image.py`: your original exercise, retained here as a reference.
2. `atom_localisation/model.py`: array coordinates, Gaussian formula and noise.
3. `atom_localisation/estimators.py`: four measurement methods.
4. `atom_localisation/experiment.py`: parameter combinations, repeated trials and summaries.
5. `atom_localisation/plots.py`: figures built from the recorded results.
6. `atom_localisation/report.py`: CSV, JSON, environment information and results narrative.
7. `run_project.py`: command-line arguments and the order of operations.

## What this project can support

You can describe it as a reproducible comparison of simple localisation methods on synthetic images, including noise, subpixel positions and a failure analysis. Its scientific value comes from checking a measurement against a known answer and explaining why a method fails.

It does not establish a new algorithm, experimentally validate atomic positions, or demonstrate machine learning. A future ML denoiser would need independent training and evaluation images, a conventional baseline and checks that denoising preserves the measured quantity.

Useful extensions include changing the centroid window, adding an asymmetric spot, simulating drift, holding total counts constant as width changes, and comparing against an experimental image with an appropriate reference measurement.

## Software references

NumPy Developers (n.d.) *Random Generator*. Available at: https://numpy.org/doc/stable/reference/random/generator.html (Accessed: 18 November 2026).

SciPy Developers (n.d.) *gaussian_filter*. Available at: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html (Accessed: 18 November 2026).

SciPy Developers (n.d.) *least_squares*. Available at: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html (Accessed: 18 November 2026).

These links describe the library operations. See `requirements.txt` and each run's metadata for the installed versions; the online stable documentation can describe newer releases.
