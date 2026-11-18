# Locating atoms in noisy images

A guided Python project exploring a materials measurement question: how does image noise affect our estimate of an atom's position?

We will start with synthetic images so that we know the true position and can check our measurements. Our first atom model will be a Gaussian bright spot. It is a simplified model, not a full simulation of electron microscopy.

## Start here

Open [the first lesson](lessons/01-images-as-arrays.md). The starter script runs as it stands and produces a blank image. Your first task is to change a few pixels and explain their positions.

From this project's folder, run:

```sh
python3 first_image.py
```

Open `outputs/first_image.png` to see the result. Running the script again replaces that file. Copy any results you want to keep before rerunning it.

NumPy and Matplotlib were available in the Python environment when this project was created. If your editor uses a different environment and reports a missing module, use a local virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python first_image.py
```

Tell your editor to use `.venv/bin/python` if you create that environment. You do not need to install anything before trying the starter with the existing environment.

## How we will work

For each step, predict what the code will do, write or change a small part, run it, and explain what happened. Keep brief notes in [research_notes.md](research_notes.md). Bring back your code, a result or an error message when you want help.

Ask for a hint when you want one. We will build the next step around what you understand, rather than completing every function in advance.

## Project milestones

| Milestone | Question | Evidence to keep |
| --- | --- | --- |
| Images as arrays | How do row and column indices relate to image position? | An image with deliberately placed bright pixels |
| A synthetic atom | How can we represent a bright spot with a continuous centre? | A Gaussian image and an explanation of its parameters |
| Noise | How does changing the noise level change the image? | Comparable images using recorded random seeds |
| Position measurement | How do the brightest-pixel and centroid methods behave? | Position estimates and errors against known centres |
| Repeated experiments | How much does the error vary between noise realisations? | Error distributions across independent trials |
| Method evaluation | When does each method become biased or unreliable? | Comparisons across positions, noise levels and spot widths |

Begin with a laptop-sized problem and NumPy. Consider filtering or machine learning after the measurement and evaluation work.

## Scientific decisions we will revisit

- A grid of pixels samples a continuous signal. A centre between pixels is worth testing once the basic image works.
- Gaussian additive noise is a useful first exercise. Counting noise and background require their own assumptions.
- A centroid depends on the chosen image region and treatment of background. It is not guaranteed to beat the brightest pixel.
- Errors measured on synthetic images describe that simulation. Experimental microscopy will require further validation.

Keep coursework and examination preparation in your schedule. Progress means being able to explain your results; there is no fixed weekly deadline.
