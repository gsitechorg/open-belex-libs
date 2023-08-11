# Belex Libs (Open Source)

Bit-Engine Language of Expressions

Version of 10 Aug 2023

# Initialization

At the moment, only conda environments are supported. The following shows how
to set up yours:

```bash
# location of your project directories
WORKSPACE="$HOME/tmp"
mkdir -p "$WORKSPACE"
cd "$WORKSPACE"

# Clone the Belex repositories (choose the same branch for all repositories):
# 1. "master" -> clone latest release code
# 2. "develop" -> clone latest development code
DEFAULT_BRANCH="develop"
BELEX_BRANCH="$DEFAULT_BRANCH"
BELEX_LIBS_BRANCH="$DEFAULT_BRANCH"

git clone --branch "$BELEX_BRANCH" git@bitbucket.org:gsitech/open-belex.git
git clone --branch "$BELEX_LIBS_BRANCH" git@bitbucket.org:gsitech/open-belex-libs.git

# Create the conda environment
cd "$WORKSPACE/open-belex-libs"
mamba env create --force -f environment.yml

conda activate open-belex-libs

pip install \
  -e "$WORKSPACE/open-belex" \
  -e "$WORKSPACE/open-belex-libs"
```
