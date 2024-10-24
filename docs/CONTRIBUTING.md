# Contributing

We welcome contributions in the form of bug reports, bug fixes, improvements to the documentation,
ideas for enhancements (or the enhancements themselves!).

You can find a [list of current issues](https://github.com/NREL/GreenHEART/issues) in the project's
GitHub repo. Feel free to tackle any existing bugs or enhancement ideas by submitting a
[pull request](https://github.com/NREL/GreenHEART/pulls).

## Bug Reports

* Please include a short (but detailed) Python snippet or explanation for reproducing the problem.
  Attach or include a link to any input files that will be needed to reproduce the error.
* Explain the behavior you expected, and how what you got differed.

## Pull Requests

* Please reference relevant GitHub issues in your commit message using `GH123` or `#123`.
* Changes should be [PEP8](http://www.python.org/dev/peps/pep-0008/) compatible.
* Keep style fixes to a separate commit to make your pull request more readable.
* Docstrings are required and should follow the
  [Google style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html).
* When you start working on a pull request, start by creating a new branch pointing at the latest
  commit on [main](https://github.com/NREL/GreenHEART).
* The GreenHEART copyright policy is detailed in the [`LICENSE`](https://github.com/NREL/GreenHEART/blob/main/LICENSE).

## Documentation

When contributing new features, or fixing existing capabilities, be sure to add and/or update the
docstrings as needed to ensure the documentation site stays up to date with the latest changes.

To build the documentation locally, the following command can be run in your terminal in the main
directory of the repository.

```bash
jupyter-book build docs/
```

In addition to generating the documentation, be sure to check the results by opening the following
path in your browser: `file:///<path-to-greenheart>/GreenHEART/docs/_build/html/index.html`.

```{note}
If the browser appears to be out of date from what you expected to built, please try the following:
1. Reload the page
2. Clear your browser's cache and open the page again.
```

## Tests

The test suite can be run using `pytest tests/greenheart`. Individual test files can be run by specifying them:

```bash
pytest tests/greenheart/test_hybrid.py
```

and individual tests can be run within those files

```bash
pytest tests/greenheart/test_hybrid.py::test_greenheart_system
```

When you push to your fork, or open a PR, your tests will be run against the
[Continuous Integration (CI)](https://github.com/NREL/HOPP/actions) suite. This will start a build
that runs all tests on your branch against multiple Python versions, and will also test
documentation builds.

## Release Process

### Standard

Most contributions will be into the `develop` branch, and once the threshold for a release has been
met the following steps should be taken to create a new release

1. On `develop`, bump the version appropriately, see the
   [semantic versioning guidelines](https://semver.org/) for details.
2. Open a pull request from `develop` into `main`.
3. When all CI tests pass, and the PR has been approved, merge the PR into main.
4. Pull the latest changes from GitHub into the local copy of the main branch.
5. Tag the latest commit to match the version bump in step 1 (replace "v0.1" in all instances below),
   and push it to the repository.

    ```bash
    git tag -a v0.1 -m "v0.1 release"
    git push --orign v0.1
    ```

6. Check that the
   [Test PyPI GitHub Action](https://github.com/NREL/GreenHEART/actions/workflows/publish_to_test_pypi.yml)
   has run successfully.
   1. If the action failed, identify and fix the issue, then
   2. delete the local and remote tag using the following (replace "v0.1" in all instances just like
      in step 5):

      ```bash
      git tag -d v0.1
      git push --delete origin v0.1
      ```

   3. Start back at step 1.
7. When the Test PyPI Action has successfully run,
   [create a new release](https://github.com/NREL/GreenHEART/releases/new) using the tag created in
   step 5.

### Patches

Any pull requests directly into the main branch that alter the GreenHEART model (excludes anything
in `docs/`, or outside of `greenheart/` and `tests/`), should be sure to follow the instructions
below:

1. All CI tests pass and the patch version has been bumped according to the
   [semantic versioning guidelines](https://semver.org/).
2. Follow steps 4 through 7 above.
3. Merge the NREL main branch back into the develop branch and push the changes.
