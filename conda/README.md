# Recipes for building ACRO conda packages

## Development

### Create a new conda environment
```
$ conda create -n test-env python=3.9
```

### Activate the conda environment
```
$ conda activate test-env
```

### Build the conda package
```
$ conda build .
```

### Install the built conda package
```
$ conda install --use-local acro
```

### Deactivate the conda environment
```
$ conda deactivate
```

### Clean up: remove the conda environment
```
$ conda env remove -n test-env
```
