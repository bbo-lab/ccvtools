# (c) 2019 Florian Franzen <Florian.Franzen@gmail.com >
import os

from imageio.core import Format

from os import SEEK_SET
import numpy as np

from ccvtools.rawio.utils import unpack_bits_16_10
from ccvtools.rawio.ccv_header import CamCommandoHeader
from construct import Int32ul, Float64l, Int64ul

import logging
logger = logging.getLogger(__name__)

class CamCommandoFormat(Format):
    """ Adds support to read ccv files with the imagio library """

    def _can_read(self, request):
        # The request object has:
        # request.filename: a representation of the source (only for reporting)
        # request.firstbytes: the first 256 bytes of the file.
        # request.mode[0]: read or write mode
        # request.mode[1]: what kind of data the user expects: one of 'iIvV?'

        try:
            # Check for CCV header
            header = CamCommandoHeader.parse(request.firstbytes)
            # Newer file version not supported
            assert (header.header_version <= 0.13)
            # Packed files with 10 bits per pixel and unpacked files with 8 bits per pixel are supported.
            if header.packed:
                assert header.bits_per_pixel == 10
            else:
                assert header.bits_per_pixel == 8
            # ToDo: Check file size based on frame count and replace asserts
        except:
            return False

        return True

    class Reader(Format.Reader):
        def _open(self):
            # Parse header
            self.header = CamCommandoHeader.parse_stream(self.request.get_file())

            self.size = (self.header.width, self.header.height)

            self.meta = {
                "size": self.size,
                "fps": self.header.frame_rate,
                "length": self.header.frame_count,
                "camera_type": self.header.camera_type.data,
                "image_type": self.header.image_type.data}

            if self.header.header_version >= 0.12:
                self.meta["sensor"] = self.header.sensor

        def _get_length(self):
            # Return number of frames
            return self.header.frame_count

        def _get_data(self, index):
            # Check if requested index is in range
            if index >= self.header.frame_count:
                raise IndexError("Image index %i > %i".format(index, self.header.frame_count))

            # Seek to request frame in file
            offset = self.header.header_size + self.header.frame_bytes_on_disk * index
            self._seek(offset)

            # Read frame from file
            dimension = (self.header.height, self.header.width)
            if self.header.packed:
                # Packed files with 10 bits per pixel
                rawdata = np.fromfile(self.request.get_file(), np.uint8,
                                      int(np.ceil(dimension[0] * dimension[1] * self.header.bits_per_pixel / 8)))
                frame = unpack_bits_16_10(rawdata).reshape(dimension)  # type: np.uint16

            else:
                # Unpacked files with 8 bits per pixel
                frame = np.fromfile(self.request.get_file(), np.uint8, dimension[0] * dimension[1]).reshape(dimension)

            # Read in additional fields
            index = Int32ul.parse_stream(self.request.get_file())
            computer_time = Float64l.parse_stream(self.request.get_file())
            cam_time = Int64ul.parse_stream(self.request.get_file())

            return frame, {"index": index,
                           "timestamp": computer_time,
                           "timestamp_computer": computer_time,
                           "timestamp_cam": cam_time,
                           }

        def _get_meta_data(self, index):
            if index is None:
                return self.meta

            # Move to end of frame
            offset = self.header.header_size \
                     + self.header.frame_bytes_on_disk * index \
                     + self.header.height * self.header.width
            self._seek(offset)

            # Read in additional fields
            index = Int32ul.parse_stream(self.request.get_file())
            computer_time = Float64l.parse_stream(self.request.get_file())
            cam_time = Int64ul.parse_stream(self.request.get_file())

            return {"index": index,
                    "timestamp": computer_time,
                    "timestamp_computer": computer_time,
                    "timestamp_cam": cam_time,
                    }

        def _seek(self, offset: int):
            try:
                self.request.get_file().seek(offset, SEEK_SET)
            except OSError as e:
                logger.error("File handle: ", self.request.get_file())
                try:
                    fd = self.request.get_file().fileno()  # Raises ValueError if closed
                    logger.error("File descriptor:", fd)
                except ValueError:
                    logger.error("Invalid or closed file object")
                    raise e
                logger.error("File: ", self.request.get_file().name)
                logger.error("File readable: ", os.access(self.request.get_file(), os.R_OK))
                logger.error("File seekable: ", self.request.get_file().seekable())
                logger.error("File position: ", self.request.get_file()._seek())
                logger.error("Requested offset: ", offset)
                logger.error("header_size: ", self.header.header_size)
                logger.error("frame_bytes_on_disk: ", self.header.frame_bytes_on_disk)
                logger.error("height: ", self.header.height)
                logger.error("width: ", self.header.width)
                raise e
