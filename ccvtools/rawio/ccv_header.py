from construct import this, Struct, Bytes, Const, If, Int64ul, Int32ul, Float64l, Byte

GreenbergString = Struct(
    "length" / Int32ul,  # > 1 < 1e3
    "data" / Bytes(this.length),
    Const(0, Byte)
)

CamCommandoHeader = Struct(
    "header_size" / Int32ul,  # < 1e5
    "camera_type" / GreenbergString,  # b'basler', b'aptina'
    "header_version" / Float64l,  # > 0 < 100 > 0.13
    "image_type" / GreenbergString,

    "bytes_per_pixel" / Int32ul,
    "bits_per_pixel" / Int32ul,
    "frame_bytes_on_disk" / Int32ul,

    "width" / Int32ul,
    "height" / Int32ul,
    "frame_rate" / Float64l,

    "packed" / If(this.header_version >= 0.12, Byte),

    "frame_count" / Int32ul,

    "sensor" / If(this.header_version >= 0.12, Struct(
        "offset" / Int32ul[2],
        "size" / Int32ul[2],
        "clock" / Int64ul,
        "exposure" / Float64l,
        "gain" / Float64l
    ))
    # ToDo: Check that we are not exceeding header size here!
)