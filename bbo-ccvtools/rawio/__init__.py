# (c) 2019 Florian Franzen <Florian.Franzen@gmail.com>

from imageio import formats

from .CamCommandoFormat import CamCommandoFormat

from .Filters import FILTERS


# Initiate and register CamCommandoFormat
_ccv_format_instance = CamCommandoFormat(
    "CamCommandoVideo",
    "Reads in BBO CamCommando videos",
    ".ccv",
    "I",  # Video only
)
formats.add_format(_ccv_format_instance)
