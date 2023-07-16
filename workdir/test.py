#!/usr/bin/env python3

from qiling.os.posix.stat import Fstat
import os


class Fake_stdin:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY)
        with open(path, 'rb') as f:
            self.buf = f.read()

    def read(self, size):
        if size <= len(self.buf):
            ret = self.buf[: size]
            self.buf = self.buf[size:]
        else:
            ret = self.buf
            self.buf = ''
        return ret

    def fstat(self):
        return Fstat(self.fd)

    def fileno(self, *args, **kwargs):
        return 0

    def show(self):
        pass

    def clear(self):
        pass

    def flush(self):
        pass

    def close(self):
        os.close(self.fd)

    def lseek(self, ofset, origin):
        pass


class Fake_stdout:
    def __init__(self, path):
        self.fd = os.open(path, os.O_APPEND | os.O_CREAT)
        self.buf = b''
        self.path = path

    def write(self, s):
        self.buf += s
        return len(s)

    def fstat(self):
        return Fstat(self.fd)

    def fileno(self):
        return 1

    def fstat64(self):
        return self.fstat()

    def close(self):
        os.close(self.fd)

    def saveToFile(self):
        with open(self.path, 'w') as f:
            f.write(self.buf.decode('utf-8'))


class Emulator():
    pass