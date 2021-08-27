Includes imageio filter and some tools to work with the CCV data format, used by the BBO lab at caesar research center

```from ccvtools import rawio``` to add ccv support to imageio.

Create a compressed movie with
```python -m ccvtools -a convert --fps 200 [ccv_file]```

The result will be in the same location with additional extension .mkv.
Alternatively, specify an output file with
```    -o [output file]```

Specify a frame idx range with
```    --idxrange [startidx] [endidx]```
Note that these are python slice indices, so first frame is 0, and
```    --idxrange 10 20```
would be equivalent to MATLABs 11:20 (sic!)
