"""fast_package_file
https://github.com/Kataiser/fast-package-file
https://fast-package-file.readthedocs.io/en/latest/
https://pypi.org/project/fast-package-file/
"""

__author__ = "Kataiser (https://github.com/Kataiser)"
__version__ = "1.1"
__copyright__ = "Copyright (c) 2019 Kataiser (https://github.com/Kataiser)"
__license__ = "MIT"

import gzip
import hashlib
import io
import json
import os
import sys
import time
import zlib
from typing import List, Union, Callable, Dict

try:
    import tqdm  # a neat progress bar
except ImportError:
    tqdm = None


class PackagedDataFile:
    def __init__(self, data_file_path: str, prepare: bool = True, decomp_func: Callable[[bytes], bytes] = None):
        """
        Prepare a packaged data file.

        :param data_file_path: Location of the package.
        :param prepare: Whether to load, decompress (if necessary), and parse the file location header now, or wait until the first file is loaded. Regardless, the entire package is not
            loaded.
        :param decomp_func: A supplied decompression function.
        """
        self.__data_file_path = data_file_path
        self.__prepared = prepare
        self.__decomp_func = decomp_func

        if prepare:
            if not os.path.exists(self.__data_file_path):  # check if file exists
                raise PackageDataError("'{}' doesn't seem to exist".format(self.__data_file_path))

            if not os.access(self.__data_file_path, os.R_OK):  # check file permissions
                raise PackageDataError("Don't have read permissions for '{}'".format(self.__data_file_path))

            with open(self.__data_file_path, 'rb') as data_file_init:
                self.__loc_data_length = int.from_bytes(data_file_init.read(8), byteorder='little')  # read header length
                if self.__loc_data_length < 0 or self.__loc_data_length > 1000000000000:  # 1 TB seems to be a reasonable limit
                    raise PackageDataError("{} is corrupted or malformed (header length is {})".format(self.__data_file_path, self.__loc_data_length))

                loc_data_raw = data_file_init.read(self.__loc_data_length)  # read the compressed header

            try:
                decomp_func_loc_data = decomp_func if decomp_func else gzip.decompress
                loc_data_bin = decomp_func_loc_data(loc_data_raw)  # decompress
            except (OSError, zlib.error):
                loc_data_bin = loc_data_raw

            try:
                self.file_data = json.loads(loc_data_bin.decode('utf-8'))  # and parse
            except json.decoder.JSONDecodeError:
                raise PackageDataError("{} is corrupted or malformed (couldn't decode JSON)".format(self.__data_file_path))
            except UnicodeDecodeError as utf8_error:
                raise PackageDataError("{} is corrupted or malformed ({})".format(self.__data_file_path, utf8_error))

    def load_file(self, file: str) -> bytes:
        """
        Load a single file from the package. Also loads and parses the location data header for the packge, if it hasn't been already.

        :param file: The path to the file, relative to the input directory (e.g. a file at surface level would be ``file.txt``, and one folder in would be ``folder\\file.txt``).
        :returns: The file as a bytes object, uncompressed.

        .. note::
            File paths stored within a package file are modified to always use backslashes as path seperators, regardless of what OS is used to build or load the package. Be sure to either
            escape the backslashes or use raw strings.
        """
        if not self.__prepared:
            self.__init__(self.__data_file_path, prepare=True, decomp_func=self.__decomp_func)  # elegant

        try:
            file_loc_data = self.file_data[file]  # get the file's stats: (offset, length, compressed (1 or 0), first byte, last byte)
        except KeyError:
            raise PackageDataError("{} is corrupted or malformed (file '{}' doesn't exist in location header)".format(self.__data_file_path, file))

        with open(self.__data_file_path, 'rb') as data_file:
            data_file.seek(file_loc_data[0] + self.__loc_data_length + 8)  # account for header and the length data
            data_file_raw = data_file.read(file_loc_data[1])

        if file_loc_data[2] == 1:  # is compressed
            try:
                if self.__decomp_func:
                    data_file_out = self.__decomp_func(data_file_raw)
                else:
                    data_file_out = gzip.decompress(data_file_raw)
            except Exception as error:
                raise PackageDataError("{} is corrupted or malformed (decompression error for {}: '{}')".format(self.__data_file_path, file, error))
        elif file_loc_data[2] == 0:
            data_file_out = data_file_raw
        else:
            raise PackageDataError("{} is corrupted or malformed (compressed state of '{}' is {}, should be 1 or 0)".format(self.__data_file_path, file, file_loc_data[2]))

        if len(file_loc_data) == 6:  # hash info exists
            if file_loc_data[5].startswith('md5   '):
                hasher = hashlib.md5()
            elif file_loc_data[5].startswith('sha256'):
                hasher = hashlib.sha256()
            else:
                raise PackageDataError("{} is corrupted or malformed (hash method seems to be '{}')".format(self.__data_file_path, file_loc_data[5][:6]))

            hasher.update(data_file_out)

            if hasher.hexdigest() != file_loc_data[5][6:]:  # confirm hash
                raise PackageDataError("{} is corrupted or malformed ('{}' hash mismatch: {} != {})".format(self.__data_file_path, file, hasher.hexdigest(), file_loc_data[5][6:]))
        else:  # basically a cheap hash
            if data_file_raw[0] != file_loc_data[3]:  # check if first byte matches
                raise PackageDataError("{} is corrupted or malformed (first byte of file '{}' should be {}, but was loaded as {})".format(
                                       self.__data_file_path, file, data_file_raw[0], file_loc_data[3]))
            elif data_file_raw[-1] != file_loc_data[4]:  # check if last byte matches
                raise PackageDataError("{} is corrupted or malformed (last byte of file '{}' should be {}, but was loaded as {})".format(
                                       self.__data_file_path, file, data_file_raw[-1], file_loc_data[4]))

        return data_file_out

    def load_bulk(self, prefix: str = '', postfix: str = '') -> Dict[str, bytes]:
        """
        Load multiple files at once, based on a prefix and/or a postfix for the file path (uses ``.startswith`` and ``.endswith``).

        :param prefix: File path prefix (e.g. a folder).
        :param postfix: File path postfix (e.g. a file extension).
        :returns: A :py:class:`dict`, formatted as ``{'path': bytes}``.
        """
        out_data = {}

        for file_in_package in self.file_data.keys():
            if file_in_package.startswith(prefix) and file_in_package.endswith(postfix):
                out_data[file_in_package] = (self.load_file(file_in_package))

        if out_data:
            return out_data
        else:
            raise PackageDataError("{} is corrupted or malformed (no file paths start with '{}' and end with '{}')".format(self.__data_file_path, prefix, postfix))

    def __repr__(self):
        """
        Includes path, number of files, and total file size.

        :returns: :py:class:`str`
        """
        return "<fast_package_file.PackagedDataFile object for {} ({} files, {} bytes)>".format(self.__data_file_path, len(self.file_data), os.stat(self.__data_file_path).st_size)


def oneshot(data_file_path: str, file: str, decomp_func: Callable[[bytes], bytes] = None) -> bytes:
    """
    Load a single file from a package file.

    :param data_file_path: Location of the package.
    :param file: The path to the file, relative to the input directory (same as :py:func:`~PackagedDataFile.load_file`).
    :param decomp_func: A supplied decompression function.
    :returns: The file as :py:class:`bytes`, uncompressed.

    .. note::
        If you're planning on ever loading another file from the same package, it's recommended to use :py:mod:`~PackagedDataFile` explicitly since it caches the file
        location data.
    """
    oneshot_package = PackagedDataFile(data_file_path, decomp_func=decomp_func)
    oneshot_file = oneshot_package.load_file(file)
    return oneshot_file


def oneshot_bulk(data_file_path: str, prefix: str = '', postfix: str = '', decomp_func: Callable[[bytes], bytes] = None) -> Dict[str, bytes]:
    """
    Combines :py:func:`oneshot` and :py:func:`~PackagedDataFile.load_bulk`. Same note as :py:func:`oneshot`.

    :param data_file_path: Location of the package.
    :param prefix: Same as :py:func:`~PackagedDataFile.load_bulk`.
    :param postfix: Same as :py:func:`~PackagedDataFile.load_bulk`.
    :param decomp_func: A supplied decompression function.
    :returns: A :py:class:`dict`, formatted as ``{'path': bytes}``.
    """
    oneshot_package = PackagedDataFile(data_file_path, decomp_func=decomp_func)
    oneshot_list = oneshot_package.load_bulk(prefix, postfix)
    return oneshot_list


# only used when reading packages
class PackageDataError(Exception):
    pass


# build a directory and all subdirectories into a single file (this part isn't fast tbh)
def build(directory: str, target: str, compress: bool = True, keep_comp_threshold: float = 0.98, hash_mode: Union[str, None] = None, comp_func: Callable[[bytes], bytes] = None,
          progress_bar: bool = True, silent: bool = False):
    """
    Build a packaged data file from a directory.

    :param directory: The directory to package. Includes all subdirectories.
    :param target: The path for the package file. If it already exists, it's overwritten.
    :param compress: Whether to compress the package, either with ``comp_func`` or Gzip by default.
    :param keep_comp_threshold: 0 through 1 (default is 0.98). For each input file, if compression doesn't improve file size by this ratio, the file is instead stored uncompressed. Set to 1 to
        compress every file no matter what.
    :param hash_mode: The hash method to use to ensure file validity. Can be "md5" or "sha256". If :py:class:`None` (the default), only the first and last bytes are compared.
    :param comp_func: A supplied decompression function that takes :py:class:`bytes` and returns :py:class:`bytes`. Some recommendations: LZMA, LZMA2, Deflate, BZip2, Oodle, or Zstandard.
    :param progress_bar: Whether to show a progress bar (uses `tqdm <https://github.com/tqdm/tqdm>`_). If tqdm isn't installed, this is irrelevant.
    :param silent: Disable all prints.
    """
    print(directory)

    start_time = time.perf_counter()
    loc_data_save = {}
    files_to_add = []
    current_loc = 0
    total_data_in = 0
    files_in = []
    gztemps_deleted = 0
    compressed_formats = ('dl_', '.gif', '.jpg', '.jpeg', '.bmp', '.png', '.wmf', '.mkv', '.mp4', '.wmv', '.avi', '.bik', '.flv', '.ogg', '.mpg', '.m2v', '.m4v', '.vob', '.mp3', '.aac',
                          '.wma', '.flac', '.zip', '.xap', '.rar', '.7z', '.cab', '.lzx', '.docx', '.xlsx', '.pptx', '.vssx', '.vstx', '.onepkg')  # list from CompactGUI

    for root, dirs, files in os.walk(directory):
        for filename_in in files:
            filename_in_joined = os.path.join(root, filename_in)  # prepare file list in order to have a progress bar

            if filename_in_joined.endswith('.gztemp'):  # in case packaging was cancelled
                os.remove(filename_in_joined)
                gztemps_deleted += 1
            else:
                files_in.append(filename_in_joined)

    if gztemps_deleted != 0 and not silent:
        print("    Deleted {} .gztemp files".format(gztemps_deleted))

    files_in.sort()

    if tqdm and not silent:
        input_iterable = tqdm.tqdm(files_in, file=sys.stdout, ncols=40, unit=' files', bar_format='    {l_bar}{bar}|', disable=not progress_bar)
    else:
        input_iterable = files_in

    for file_path in input_iterable:
        with open(file_path, 'rb') as input_file:
            input_file_data_raw = input_file.read()

        total_data_in += len(input_file_data_raw)
        is_compressed = [c_format for c_format in compressed_formats if file_path.endswith(c_format)]  # check file extension

        if compress and not is_compressed:
            if comp_func:
                input_file_data_comp = comp_func(input_file_data_raw)
            else:
                input_file_data_comp = _gzip_compress_fix(input_file_data_raw)

            if len(input_file_data_comp) < len(input_file_data_raw) * keep_comp_threshold:  # if compression improves file size
                input_file_data = input_file_data_comp
                compressed = True
                gz_path = '{}.gztemp'.format(file_path)  # because storing every file's data takes too much memory
                files_to_add.append(gz_path)

                with open(gz_path, 'wb') as temp_gz:
                    temp_gz.write(input_file_data)
            else:
                # if compression doesn't improve file size (much)
                input_file_data = input_file_data_raw
                compressed = False
                files_to_add.append(file_path)
        else:
            # skipping gzip testing because file is likely already compressed based on extension
            input_file_data = input_file_data_raw
            compressed = False
            files_to_add.append(file_path)

        file_path_short = file_path[len(directory) + len(os.sep):]  # removes some redundancy
        file_path_out = file_path_short.replace(os.sep, '\\')  # makes building uniform across OSs
        loc_data_save[file_path_out] = [current_loc, len(input_file_data), 1 if compressed else 0, input_file_data[0], input_file_data[-1]]  # add file to header dictionary
        current_loc += len(input_file_data)  # keep track of offset

        # calculate and add hash, if enabled
        if hash_mode == 'md5':
            hasher = hashlib.md5()
            hasher.update(input_file_data_raw)
            loc_data_save[file_path_out].append('md5   {}'.format(hasher.hexdigest()))
        elif hash_mode == 'sha256':
            hasher = hashlib.sha256()
            hasher.update(input_file_data_raw)
            loc_data_save[file_path_out].append('sha256{}'.format(hasher.hexdigest()))

    comp_func_loc_data = comp_func if (comp_func and compress) else _gzip_compress_fix
    loc_data_save_json = json.dumps(loc_data_save, separators=(',', ':'), sort_keys=True).encode('utf-8')  # convert header to binary
    loc_data_save_out = comp_func_loc_data(loc_data_save_json) if compress else loc_data_save_json  # and compress it
    loc_data_save_length = (len(loc_data_save_out)).to_bytes(8, byteorder='little')  # get its length as an 8 bit binary

    with open(target, 'wb') as out_file:
        out_file.write(loc_data_save_length)  # add the header's length
        out_file.write(loc_data_save_out)  # add the header

        for file_to_add_path in files_to_add:
            with open(file_to_add_path, 'rb') as file_to_add:  # add the files from either the original data or its .gztemp
                out_file.write(file_to_add.read())

            if file_to_add_path.endswith('.gztemp'):  # and then delete the .gztemp
                os.remove(file_to_add_path)

    if not silent:
        # monitoring output
        duration = format(time.perf_counter() - start_time, '.2f')
        input_size = format(total_data_in / 1048576, '.2f')
        target_size = format(os.stat(target).st_size / 1048576, '.2f')
        print("    {} ({} MB, {} files) -> {} ({} MB) took {} seconds".format(directory, input_size, len(files_in), target, target_size, duration))


# basically gzip.compress(), but deterministic (mtime=0)
def _gzip_compress_fix(data: bytes) -> bytes:
    buffer = io.BytesIO()

    with gzip.GzipFile(mode='wb', fileobj=buffer, mtime=0) as temp_file:
        temp_file.write(data)

    return buffer.getvalue()


if __name__ == '__main__':
    pass
