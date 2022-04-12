# ccvtools
Includes imageio filter and some commandline tools to work with the CCV data format, used by the BBO lab at MPI-NB.

## Installation
Install with `pip install bbo-ccvtools`.

## Usage
### Imageio
```from ccvtools import rawio``` to add ccv support to imageio.

### Command line
#### Create a compressed movie with
```python -m ccvtools -a convert --quality [quality between 1 and 10, suggestion 7] --fps [your frame rate] [ccv_file]```

The result will be in the same location with additional extension .mkv.
Alternatively, specify an output file with `-o [output file]`.

Specify a frame idx range with `--idxrange [startidx] [endidx]`.
Note that these are python slice indices, so first frame is 0, and `--idxrange 10 20` would be equivalent to MATLABs 11:20 (sic!).
