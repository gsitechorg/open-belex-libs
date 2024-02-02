# Belex Libs (Open Source)

Miscellaneous libraries for the Bit-Engine Language of Expressions (Belex) of
GSI's APU.

Version of 02-Feb-2024

# Initialization

At the moment, only conda environments are supported. The following shows how
to set up yours:

```bash
# let $WORKSPACE be the parent working directory of open-belex-libs
cd "$WORKSPACE"

# Clone the open-belex repositories (unless you know what you are doing,
# please choose the same branch for all repositories):
# 1. "master" -> clone latest release code
# 2. "develop" -> clone latest development code
DEFAULT_BRANCH="master"
BELEX_BRANCH="$DEFAULT_BRANCH"
BELEX_LIBS_BRANCH="$DEFAULT_BRANCH"

git clone --branch "$BELEX_BRANCH" \
    https://github.com/gsitechorg/open-belex.git
git clone --branch "$BELEX_LIBS_BRANCH" \
    https://github.com/gsitechorg/open-belex-libs.git

cd open-belex-libs

# Create the conda environment
mamba env create --force -f environment.yml
conda activate open-belex-libs

# Tell pip to use the cloned versions of open-belex and open-belex-libs
pip install -e ../open-belex -e .
```
