# BELEX, THE REPO

Bit-Engine Language of Expressions

Version of 06 Jan 2022

# SET UP PYTHON AND REQUIREMENTS

Make sure you have a virtual environment of some kind that has the
necessary Python packages installed. Here is an example using `venv`, but you
may use `conda` just as easily:

```bash
  cd ~/GSI  # or wherever you likd to keep your project directories

  # Clone the Belex repositories (choose the same branch for all repositories):
  # 1. "--branch master" -> clone latest release code
  # 2. "--branch develop" -> clone latest development code
  git clone --branch develop git@bitbucket.org:gsitech/belex.git
  git clone --branch develop git@bitbucket.org:gsitech/belex-libs.git
  git clone --branch develop git@bitbucket.org:gsitech/belex-tests.git

  # Initialize your virtual environment
  cd ~/GSI/belex-tests  # or wherever you cloned the belex-tests repo
  python -m venv venv  # you need Python>=3.8
  source venv/bin/activate

  cd ~/GSI/belex  # or wherever you cloned the belex repo
  pip install -e .

  cd ~/GSI/belex-libs  # or wherever you cloned the belex-libs repo
  pip install -e .

  cd ~/GSI/belex-tests  # or wherever you cloned the belex-tests repo
  pip install -e .
  
  pip install --upgrade ninja
  pip install \
      --upgrade \
      --index-url http://192.168.42.9:8081/repository/gsi-pypi/simple \
      --trusted-host 192.168.42.9 \
      meson
```
