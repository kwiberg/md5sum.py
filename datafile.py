import struct
import zlib

class DatafileError(Exception):
    pass

class Datafile(object):
    @classmethod
    def encode(cls, data):
        return data
    @classmethod
    def decode(cls, version, data):
        return data
    @classmethod
    def read(cls, filename):
        with open(filename, 'rb') as f:
            try:
                [magic, version] = struct.unpack('<QL', f.read(12))
            except struct.error:
                raise DatafileError('Could not read file header')
            if magic != cls.magic:
                raise DatafileError(
                    ('Wrong magic number (expected 0x{:x},'
                     ' got 0x{:x})').format(cls.magic, magic))
            try:
                d = zlib.decompress(f.read())
            except zlib.error as e:
                raise DatafileError(str(e))
            return cls.decode(version, d)
    @classmethod
    def write(cls, filename, data):
        with open(filename, 'wb') as f:
            f.write(struct.pack('<QL', cls.magic, cls.version))
            f.write(zlib.compress(cls.encode(data)))
