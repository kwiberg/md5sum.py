import binascii
import errno
import gzip
import hashlib
import hsum.datafile as hd
import optparse
import os
import os.path as op
import pickle
import sys
import time

class Cachefile(hd.Datafile):
    magic = 0x7206fab738a48740
    version = 0
    @classmethod
    def encode(cls, data):
        return pickle.dumps(data)
    @classmethod
    def decode(cls, version, data):
        if version != 0:
            raise hd.DatafileError('Unsupported version ({})'.format(version))
        return pickle.loads(data)

def stat(f):
    '''Return a tuple of stat numbers that should change whenever the
    file contents change.'''
    s = os.fstat(f.fileno())
    return (s.st_ino, s.st_size, s.st_mtime, s.st_ctime)

def md5(f):
    '''Consume the remainder of the file and return its md5 hash.'''
    h = hashlib.md5()
    for x in iter(lambda: f.read(2**20), b''):
        h.update(x)
    return h.digest()

class TreeHash(object):
    __maxtime = 3600 * 24 * 30 # max age of a cached hash, in seconds
    def __init__(self, rootdir, cachefile):
        assert isinstance(rootdir, bytes)
        self.__rootdir = rootdir
        self.__cachefile = cachefile
        self.__cache = {} # fn -> (stat, time, hash)
        self.__read_cachefile()
    def __read_cachefile(self):
        assert not self.__cache
        if not self.__cachefile:
            return
        try:
            self.__cache = Cachefile.read(self.__cachefile)
        except hd.DatafileError as e:
            print('Could not load cachefile:\n  {}'.format(e),
                  file = sys.stderr)
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass # cachefile doesn't exist, but that's OK
            else:
                print('Could not load cachefile:\n  {}'.format(e),
                      file = sys.stderr)
        except (pickle.PickleError, ValueError):
            print('Malformed cachefile', file = sys.stderr)
    def write_cachefile(self):
        if not self.__cachefile:
            return
        try:
            Cachefile.write(self.__cachefile, self.__cache)
        except IOError as e:
            print('Could not write cachefile:\n  {}'.format(e),
                  file = sys.stderr)
    def hash_file(self, fn):
        '''Return the hash of a single file (path given relative to
        the TreeHash's root directory.)'''
        assert isinstance(fn, bytes)
        with open(op.join(self.__rootdir, fn), 'rb') as f:
            s = stat(f)
            if fn in self.__cache:
                (s0, t0, h0) = self.__cache[fn]
                if s == s0 and time.time() < t0 + self.__maxtime:
                    return h0
            h = md5(f)
            self.__cache[fn] = (s, time.time(), h)
            return h
    def __iter_files(self, subdir):
        '''Yield the path (relative to the TreeHash's root directory)
        of all files in the subtree rooted att subdir.'''
        assert isinstance(subdir, bytes)
        for fn in os.listdir(op.join(self.__rootdir, subdir)):
            fn_full = op.join(self.__rootdir, subdir, fn)
            if op.isfile(fn_full):
                yield op.join(subdir, fn)
            elif op.isdir(fn_full) and not op.islink(fn_full):
                for fn2 in self.__iter_files(op.join(subdir, fn)):
                    yield fn2
    def hash_dir(self, subdir = b''):
        '''Yield the path (relative to the TreeHash's root directory)
        and hash of all files in the subtree rooted att subdir. The
        files are yielded in alphabetical order (sorted on the bytes
        in the filenames).'''
        for fn in sorted(self.__iter_files(subdir)):
            yield (fn, self.hash_file(fn))

def main():
    parser = optparse.OptionParser()
    parser.add_option(
        '-C', '--cachefile', help = 'cache md5sums in FILE', metavar = 'FILE')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        print('Must specify exactly one directory', file = sys.stderr)
        sys.exit(1)
    [rootdir] = [a.encode() for a in args]
    th = TreeHash(rootdir, options.cachefile)
    for (fn, h) in th.hash_dir():
        print('{}  {}'.format(binascii.hexlify(h).decode(), fn.decode()))
    th.write_cachefile()

if __name__ == '__main__':
    main()
