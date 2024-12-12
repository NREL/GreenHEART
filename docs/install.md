# Installing GreenHeart

```bash
pip install greenheart
```

## NREL Resource Data

1. The functions which download resource data require an NREL API key. Obtain a key from:

    [https://developer.nrel.gov/signup/](https://developer.nrel.gov/signup/)

2. To set up the `NREL_API_KEY` and `NREL_API_EMAIL` required for resource downloads, you can create
   Environment Variables called `NREL_API_KEY` and `NREL_API_EMAIL`. Otherwise, you can keep the key
   in a new file called ".env" in the root directory of this project.

    Create a file ".env" that contains the single line:

    ```bash
    NREL_API_KEY=key
    NREL_API_EMAIL=your.name@email.com
    ```

## Installing from Source

For most use cases, installing from source will be the preferred installation route.

### NREL-Provided Conda Environment Specification (recommended)

1. Using Git, navigate to a local target directory and clone repository:

    ```bash
    git clone https://github.com/NREL/GreenHEART.git
    ```

2. Navigate to `GreenHEART`

    ```bash
    cd GreenHEART
    ```

3. (Optional) If using NREL resource data, you will need an NREL API key, which can be obtined from:
    [https://developer.nrel.gov/signup/](https://developer.nrel.gov/signup/)

    1. In `environment.yml`, add the following lines to the bottom of the file, and replace the
       items in angle brackets (`<>`), including the brackets with your information. Be sure that
       "variables" has no leading spaces

        ```yaml
        variables:
          NREL_API_KEY=<API-KEY>
          NREL_API_EMAIL=<email-address>
        ```

4. Create a conda environment and install GreenHEART and all its dependencies

    ```bash
    conda env create -f environment.yml
    ```

5. Install Cbc.
   1. If using a Unix machine (not Windows), install a final dependency

        ```bash
        conda install -y -c conda-forge coin-or-cbc=2.10.8
        ```

    2. Windows users will have to manually install Cbc: https://github.com/coin-or/Cbc

An additional step can be added if additional dependencies are required, or you plan to use this
environment for development work.

- Pass `-e` for an editable developer install
- Use one of the extra flags as needed:
  - `examples`: allows you to use the Jupyter Notebooks
  - `develop`: adds developer and documentation tools
  - `all` simplifies adding all the dependencies

This looks like the following for a developer installation:

```bash
pip install -e ".[all]"
```

### Manual steps

1. Using Git, navigate to a local target directory and clone repository:

    ```bash
    git clone https://github.com/NREL/GreenHEART.git
    ```

2. Navigate to `GreenHEART`

    ```bash
    cd GreenHEART
    ```

3. Create a new virtual environment and change to it. Using Conda Python 3.11 (choose your favorite
   supported version) and naming it 'greenheart' (choose your desired name):

    ```bash
    conda create --name greenheart python=3.11 -y
    conda activate greenheart
    ```

4. Install GreenHEART and its dependencies:

    ```bash
    conda install -y -c conda-forge glpk
    ```

    ````{note}
    Unix users should install Cbc via:

    ```bash
    conda install -y -c conda-forge coin-or-cbc=2.10.8
    ```

    Windows users should install Cbc manually according to https://github.com/coin-or/Cbc.
    ````

    - If you want to just use GreenHEART:

       ```bash
       pip install .
       ```

    - If you want to work with the examples:

       ```bash
       pip install ".[examples]"
       ```

    - If you also want development dependencies for running tests and building docs:

       ```bash
       pip install -e ".[develop]"
       ```

    - In one step, all dependencies can be installed as:

      ```bash
      pip install -e ".[all]"
      ```

## Developer Notes

Developers should add install using `pip install -e ".[all]"` to ensure documentation testing, and
linting can be done without any additional installation steps.

Please be sure to also install the pre-commit hooks if contributing code back to the main
repository via the following. This enables a series of automated formatting and code linting
(style and correctness checking) to ensure the code is stylistically consistent.

```bash
pre-commit install
```

If a check (or multiple) fails (commit is blocked), and reformatting was done, then restage
(`git add`) your files and commit them again to see if all issues were resolved without user
intervention. If changes are required follow the suggested fix, or resolve the stated
issue(s). Restaging and committing may take multiple attempts steps if errors are unaddressed
or insufficiently addressed. Please see [pre-commit](https://pre-commit.com/),
[ruff](https://docs.astral.sh/ruff/), or [isort](https://pycqa.github.io/isort/) for more
information.
