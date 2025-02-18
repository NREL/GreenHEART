# Examples Overview

This directory provides example Jupyter notebooks demonstrating how to use the GreenHEART tool for technoeconomic analysis of green technology applications. These workflows and calculations cover hydrogen production, steel manufacturing, ammonia synthesis, and Proton Exchange Membrane (PEM) electrolyzer modeling. GreenHEART enables co-design and simulation of an integrated renewable energy and hydrogen production plant, along with optional end-use applications.

The first three notebooks focus on the GreenHEART simulation interface, which supports single analysis cases as well as optimization for levelized cost of product. The final example, `04-PEM_electrolyzer.ipynb`, illustrates how to use GreenHEART's PEM electrolyzer model.

## Structure

- **01-green-hydrogen.ipynb**: Demonstrates a workflow for green hydrogen production using renewable energy and electrolysis.
- **02-green-steel.ipynb**: Illustrates green steel production using hydrogen as a reducing agent via hydrogen direct reduced iron and electric arc furnace (HDRI-EAF) technology.
- **03-green-ammonia.ipynb**: Covers green ammonia production through renewable hydrogen in the Haber-Bosch process.
- **04-PEM_electrolyzer.ipynb**: Details the use of the GreenHEART PEM Water Electrolyzer model, including key components and operation.

## Quick Start
1. Clone the repository:
    ```bash
    git clone https://github.com/NREL/GreenHEART.git
    ```
2. Create a conda environment from the `environment.yml`:
    ```bash
    conda env create -f environment.yml
    ```
3. The functions which download resource data require an NREL API key. Obtain a key from:

    [https://developer.nrel.gov/signup/](https://developer.nrel.gov/signup/)

4. To set up the `NREL_API_KEY` and `NREL_API_EMAIL` required for resource downloads, you can create
   Environment Variables called `NREL_API_KEY` and `NREL_API_EMAIL`. Otherwise, you can keep the key
   in a new file called ".env" in the root directory of this project.

    Create a file ".env" that contains the single line:

    ```bash
    NREL_API_KEY=key
    NREL_API_EMAIL=your.name@email.com
    ```
5. Open a Jupyter Notebook environment to explore the examples:

    ```bash
   jupyter notebook
   ```

**OR**
1. Clone the repository:
    ```bash
    git clone https://github.com/NREL/GreenHEART.git
    ```
2. Follow the setup instructions in the main `README.md`
3. Open a Jupyter Notebook environment to explore the examples:

    ```bash
   jupyter notebook
   ```
