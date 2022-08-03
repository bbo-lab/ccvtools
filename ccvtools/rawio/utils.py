import numpy as np


def unpack_bits_16_10(input_array: np.ndarray):
  
    """Unpacks data into uint16 values from uint8 packed values. Length of each sample(or pixel) is 10 bits."""
    # Written based on bboanalysis_m/datamanipulation/unpack_bits.cpp and C++ funtion 'unpack_bits_16_10' in 'bboanalysis_m/camera cpp code/dgpackbits.h'.

    nbytes_in = input_array.size
    nsamples_in = int(np.floor(nbytes_in * 8.0 / 10.0))

    bytes_per_sample_unpacked = 2  # int(np.ceil(10.0 / 8.0))
    nbytes_out = bytes_per_sample_unpacked * nsamples_in

    nblocks = nsamples_in / 4.0
    nblocks_floor = int(np.floor(nblocks))

    # The final output array
    output_array = np.zeros(nbytes_out, dtype='uint8')

    input_array_1 = input_array[:5 * nblocks_floor].reshape(nblocks_floor, 5)
    output_array_1 = np.zeros((nblocks_floor, 8), dtype='uint8')

    # Process the data in blocks of 40 bits of data = 4 samples = 8 unpacked bytes = 5 packed bytes
    output_array_1[:, 0] = input_array_1[:, 0]
    output_array_1[:, 1] = input_array_1[:, 1] & 3
    output_array_1[:, 2] = (input_array_1[:, 1] >> 2) | (
            (input_array_1[:, 2] & 3) << 6)
    output_array_1[:, 3] = (input_array_1[:, 2] >> 2) & 3
    output_array_1[:, 4] = (input_array_1[:, 2] >> 4) | \
                                        (input_array_1[:, 3] << 4)
    output_array_1[:, 5] = (input_array_1[:, 3] >> 4) & 3
    output_array_1[:, 6] = (input_array_1[:, 3] >> 6) | \
                                        (input_array_1[:, 4] << 2)
    output_array_1[:, 7] = input_array_1[:, 4] >> 6

    output_array[:8 * nblocks_floor] = output_array_1.flatten()

    # Unpacking the remaining samples after the blocks
    remaining_samples = nsamples_in - (4 * nblocks_floor)

    if remaining_samples != 0:
        byte_offset_in = int(5 * nblocks_floor)
        byte_offset_out = int(8 * nblocks_floor)
        
        output_array[byte_offset_out] = input_array[byte_offset_in]
        output_array[byte_offset_out + 1] = input_array[byte_offset_in + 1] & 3
        
        if remaining_samples > 1:
            output_array[byte_offset_out + 2] = (input_array[byte_offset_in + 1] >> 2) | \
                                                ((input_array[byte_offset_in + 2] & 3) << 6)
            output_array[byte_offset_out + 3] = (input_array[byte_offset_in + 2] >> 2) & 3
            
            if remaining_samples > 2:
                output_array[byte_offset_out + 4] = (input_array[byte_offset_in + 2] >> 4) | \
                                                    (input_array[byte_offset_in + 3] << 4)
                output_array[byte_offset_out + 5] = (input_array[byte_offset_in + 3] >> 4) & 3
    
    # Two unpacked bytes per pixel are processed into uint16 value.
    output_array = output_array.astype('uint16').reshape(-1, 2)
    output_array = (output_array[:, 1] << 8) | output_array[:, 0]
    
    return output_array
