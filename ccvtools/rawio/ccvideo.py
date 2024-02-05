from pathlib import Path

from os import SEEK_SET, SEEK_END
import numpy as np

from ccvtools.rawio.ccv_header import CamCommandoHeader
from ccvtools.rawio.utils import unpack_bits_16_10

from construct import Int32ul, Float64l


class CamCommandoVideo:
    def __init__(self, filename, rw=False):
        self.filename = Path(filename)
        self._fh = None  # Lazy initialization, only access via get_file_handle
        self._rw = rw
        self._header_written = False  # The header has been written and may not change in length anymore
        self._header_updated = False  # The header construct has been updated and needs to be written to the file

        if self.filename.is_file():
            self.read_header()
            self._header_written = True
        else:
            self.header = CamCommandoHeader.parse(Int32ul.build(106) + 102 * b'\00')

    def __del__(self):
        self.close()

    def __len__(self):
        return self.header.frame_count

    def close(self):
        if self._header_updated:
            self.write_header()
        if self._fh is not None:
            self._fh.close()

    def get_file_handle(self):
        if self._fh is None:
            if self._rw:
                file_mode = 'r+b'
            else:
                file_mode = 'rb'
            if not self.filename.is_file():
                with open(self.filename, 'wb'):
                    pass

            self._fh = open(self.filename, file_mode)
        return self._fh

    def read_header_length(self, file_name=None):
        if file_name is None:
            fh = self.get_file_handle()
            fh.seek(0)
            header_length = int.from_bytes(fh.read(4), 'little')
        else:
            with open(file_name, 'rb') as fh:
                header_length = int.from_bytes(fh.read(4), 'little')
        return header_length

    def read_header(self):
        header_length = self.read_header_length()
        assert header_length < 1024, "Header is too long, you are probably not using a CCV file"
        fh = self.get_file_handle()
        fh.seek(0)
        self.header = CamCommandoHeader.parse(fh.read(header_length))

    def copy_header_from_file(self, file_name, zero_frame_count=True):
        header_length = self.read_header_length(file_name)
        assert header_length < 1024, "Header is too long, you are probably not using a CCV file"
        with open(file_name, 'rb') as fh:
            self.header = CamCommandoHeader.parse(fh.read(header_length))
        if zero_frame_count:
            self.header.frame_count = 0
        self._header_updated = True

    def write_header(self):
        if self._header_updated:
            header_bytes = CamCommandoHeader.build(self.header)
            if self._header_written:
                header_length = self.read_header_length()
                assert header_length == len(header_bytes), (
                    "Currently, we cannot write a header with a length different "
                    "from the original one.")
            fh = self.get_file_handle()
            fh.seek(0)
            fh.write(header_bytes)
            self._header_written = True
            self._header_updated = False

    def read_image(self, index=None, return_time=True):
        fh = self.get_file_handle()

        # Check if requested index is in range
        if index is not None:
            if index >= self.header.frame_count:
                raise IndexError(f"Image index {index} > {self.header.frame_count}")

            # Seek to request frame in file
            offset = self.header.header_size + self.header.frame_bytes_on_disk * index
            fh.seek(offset, SEEK_SET)

        # Read frame from file
        dimension = (self.header.height, self.header.width)
        if self.header.packed:
            # Packed files with 10 bits per pixel
            rawdata = np.fromfile(fh, np.uint8,
                                  int(np.ceil(dimension[0] * dimension[1] * self.header.bits_per_pixel / 8)))
            frame = unpack_bits_16_10(rawdata).reshape(dimension)  # type: np.uint16

        else:
            # Unpacked files with 8 bits per pixel
            frame = np.fromfile(fh, np.uint8, dimension[0] * dimension[1]).reshape(dimension)

        index = Int32ul.parse_stream(fh)
        timestamp = Float64l.parse_stream(fh)
        rest = fh.read(9)

        if return_time:
            # Read in additional fields

            return frame, {"index": index, "timestamp": timestamp, 'rest': rest}
        else:
            return frame

    def append_image(self, image: np.ndarray, index=None, meta=None):
        assert not self.header.packed, "Packed images currently not supported"
        assert image.dtype == np.uint8, "Only np.uint8 images are supported"

        if not self._header_written:
            self.write_header()

        if meta is None:
            meta = dict()
        meta_default = {
            "index": index,
            "timestamp": 0,
            "rest": 9 * b'\0',  # No idea what this is. Once found out, will be replaced
        }
        for key in meta_default:
            if key not in meta:
                meta[key] = meta_default[key]

        if index == -1:
            meta["index"] = self.header.frame_count
        elif index is not None:
            meta["index"] = index

        fh = self.get_file_handle()
        fh.seek(0, SEEK_END)
        pos = fh.tell()
        fh.write(image.tobytes())
        fh.write(Int32ul.build(meta["index"]))
        fh.write(Float64l.build(meta["timestamp"]))
        fh.write(meta["rest"])
        bytes_missing = self.header.frame_bytes_on_disk - (fh.tell() - pos)
        assert bytes_missing == 0, (f"Written {bytes_missing} bytes too few. File is corrupt now!")

        self.header.frame_count += 1
        self._header_updated = True
