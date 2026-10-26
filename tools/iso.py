import struct
class Iso:
    """Minimal ISO9660 root-directory reader (the SH2 discs keep everything but MODULES at the root)."""
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.f.seek(16 * 2048); pvd = self.f.read(2048)
        assert pvd[1:6] == b'CD001', path
        root = pvd[156:156 + 34]
        lba, size = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
        self.files = {}
        self.f.seek(lba * 2048); d = self.f.read(size); i = 0
        while i < len(d):
            n = d[i]
            if n == 0: i = (i // 2048 + 1) * 2048; continue
            flba, fsz = struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]
            name = d[i + 33:i + 33 + d[i + 32]].decode('ascii', 'replace').split(';')[0]
            self.files[name] = (flba, fsz); i += n
    def read(self, name, off=0, size=None):
        lba, fsz = self.files[name]
        self.f.seek(lba * 2048 + off)
        return self.f.read(fsz - off if size is None else size)
