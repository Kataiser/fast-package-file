import os
import unittest

import fast_package_file


class TestTF2RichPresenseFunctions(unittest.TestCase):
    # tests building packages against the reference builds
    def test_build(self):
        if [ref for ref in ref_list if not os.path.exists(ref)]:
            # build references only if needed
            build_references()

        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[0])
        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[1], compress=False)
        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[2])
        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[3], hash_mode='md5', compress=False)
        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[4])
        fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), test_list[5], hash_mode='sha256', compress=False)

        file_data = {}
        for file in ref_list + test_list:
            with open(file, 'rb') as file_opened:
                file_data[file] = file_opened.read()

        for ref in ref_list:
            try:
                self.assertEqual(file_data[ref.replace('ref', 'test')], file_data[ref])
            except AssertionError:
                print(file_data[ref.replace('ref', 'test')])
                print(file_data[ref])
                raise

    # test loading the file location data
    def test_package_init(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        for test_file in test_list:
            self.assertTrue(repr(fast_package_file.PackagedDataFile(test_file)).startswith('<fast_package_file.PackagedDataFile object for {} ('.format(test_file)))

    # test loading a file against the actual file
    def test_load_file(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        for test_file in test_list:
            test_file_loaded = fast_package_file.PackagedDataFile(test_file)

            with open(os.path.join('test_dir', 'docs_v1.0_testing', 'index.rst'), 'rb') as dist_file_ref:
                dist_file_ref_data = dist_file_ref.read()

                self.assertEqual(test_file_loaded.load_file('index.rst'), dist_file_ref_data)

            with open(os.path.join('test_dir', 'docs_v1.0_testing', '_build', 'html', 'index.html'), 'rb') as dist_file_ref:
                dist_file_ref_data = dist_file_ref.read()

                self.assertEqual(test_file_loaded.load_file(r'_build\html\index.html'), dist_file_ref_data)

    # test loading a directory
    def test_load_bulk(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        with open(os.path.join('test_dir', 'docs_v1.0_testing', '_build', 'doctrees', 'environment.pickle'), 'rb') as environment_pickle:
            environment_pickle_ref = environment_pickle.read()
        with open(os.path.join('test_dir', 'docs_v1.0_testing', '_build', 'html', 'genindex.html'), 'rb') as genindex_html:
            genindex_html_ref = genindex_html.read()

        for test_file in test_list:
            test_file_loaded = fast_package_file.PackagedDataFile(test_file)

            self.assertEqual(test_file_loaded.load_bulk(prefix=r'_build\doctrees')[0], environment_pickle_ref)
            self.assertEqual(test_file_loaded.load_bulk(prefix=r'_build\html', postfix='.html')[0], genindex_html_ref)

    # test a variety of possible loading errors
    def test_errors(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        # for PackagedDataFile.__init__()
        with self.assertRaises(fast_package_file.PackageDataError) as e:
            fast_package_file.PackagedDataFile('a non-existent file')
        self.assertEqual(e.exception.args[0], "'a non-existent file' doesn't seem to exist")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_compressed.data'), 'rb') as test_compressed_data:
                with open(os.path.join('test_dir', 'test_compressed_bad_header.data'), 'wb') as test_compressed_bad_header:
                    test_compressed_bad_header.write(test_compressed_data.read()[1:])

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_compressed_bad_header.data'))
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (header length is 2233785415175766017)".format(os.path.join('test_dir', 'test_compressed_bad_header.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_compressed.data'), 'rb') as test_compressed_data:
                test_compressed_data_read = test_compressed_data.read()

                with open(os.path.join('test_dir', 'test_compressed_bad_json.data'), 'wb') as test_compressed_bad_header:
                    test_compressed_bad_header.write(test_compressed_data_read[:100])
                    test_compressed_bad_header.write(test_compressed_data_read[120:])

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_compressed_bad_json.data'))
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (couldn't decompress header: Error -3 while decompressing data: invalid distance too far back)".format(
                                              os.path.join('test_dir', 'test_compressed_bad_json.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_uncompressed.data'), 'rb') as test_uncompressed_data:
                test_uncompressed_data_read = test_uncompressed_data.read()

                with open(os.path.join('test_dir', 'test_uncompressed_bad_json.data'), 'wb') as test_uncompressed_bad_header:
                    test_uncompressed_bad_header.write(test_uncompressed_data_read[:100])
                    test_uncompressed_bad_header.write(test_uncompressed_data_read[120:])

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_uncompressed_bad_json.data'))
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (couldn't decode JSON)".format(os.path.join('test_dir', 'test_uncompressed_bad_json.data')))

        # for PackagedDataFile.load_file()
        with self.assertRaises(fast_package_file.PackageDataError) as e:
            test_compressed_data = fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_compressed.data'))
            test_compressed_data.load_file('a non-existent file')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (file 'a non-existent file' doesn't exist in location header)".format(
                                              os.path.join('test_dir', 'test_compressed.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_uncompressed.data'), 'rb') as test_uncompressed_data:
                with open(os.path.join('test_dir', 'test_uncompressed_bad_cstate.data'), 'wb') as test_uncompressed_bad_cstate:
                    test_uncompressed_bad_cstate.write(test_uncompressed_data.read().replace(b',0,', b',2,'))

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_uncompressed_bad_cstate.data')).load_file('index.rst')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (compressed state of 'index.rst' is 2, should be 1 or 0)".format(
                                              os.path.join('test_dir', 'test_uncompressed_bad_cstate.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_md5_uncompressed.data'), 'rb') as test_md5_uncompressed_data:
                with open(os.path.join('test_dir', 'test_md5_uncompressed_bad_hash_method.data'), 'wb') as test_md5_uncompressed_bad_hash_method_data:
                    test_md5_uncompressed_bad_hash_method_data.write(test_md5_uncompressed_data.read().replace(b',"md5   ', b',"mi6   '))

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_md5_uncompressed_bad_hash_method.data')).load_file('index.rst')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (hash method seems to be 'mi6   ')".format(
                                              os.path.join('test_dir', 'test_md5_uncompressed_bad_hash_method.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_md5_uncompressed.data'), 'rb') as test_md5_uncompressed_data:
                test_md5_uncompressed_data_read = test_md5_uncompressed_data.read()

                with open(os.path.join('test_dir', 'test_md5_uncompressed_bad_filedata.data'), 'wb') as test_md5_uncompressed_bad_filedata_data:
                    test_md5_uncompressed_bad_filedata_data.write(test_md5_uncompressed_data_read[:3000])
                    test_md5_uncompressed_bad_filedata_data.write(test_md5_uncompressed_data_read[3500:])

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_md5_uncompressed_bad_filedata.data')).load_file('conf.py')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed ('conf.py' hash mismatch: 3a335971d1353e3bb7e4e293ee6444bc != e0bff95e9ef5da195903c03bd057d282)".format(
                                              os.path.join('test_dir', 'test_md5_uncompressed_bad_filedata.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open(os.path.join('test_dir', 'test_uncompressed.data'), 'rb') as test_uncompressed_data:
                test_uncompressed_data_read = test_uncompressed_data.read()

                with open(os.path.join('test_dir', 'test_uncompressed_bad_filedata.data'), 'wb') as test_uncompressed_bad_filedata_data:
                    test_uncompressed_bad_filedata_data.write(test_uncompressed_data_read[:3000])
                    test_uncompressed_bad_filedata_data.write(test_uncompressed_data_read[3500:])

            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_uncompressed_bad_filedata.data')).load_file('conf.py')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (last byte of file 'conf.py' should be 110, but was loaded as 10)".format(
                                              os.path.join('test_dir', 'test_uncompressed_bad_filedata.data')))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            fast_package_file.PackagedDataFile(os.path.join('test_dir', 'test_compressed.data')).load_bulk(prefix='pre', postfix='post')
        self.assertEqual(e.exception.args[0], "{} is corrupted or malformed (no file paths start with 'pre' and end with 'post')".format(
                                              os.path.join('test_dir', 'test_compressed.data')))

        for file_to_delete in ['test_compressed_bad_header.data', 'test_compressed_bad_json.data', 'test_md5_uncompressed_bad_filedata.data', 'test_md5_uncompressed_bad_hash_method.data',
                               'test_uncompressed_bad_cstate.data', 'test_uncompressed_bad_filedata.data', 'test_uncompressed_bad_json.data']:
            os.remove(os.path.join('test_dir', file_to_delete))


# build reference package files
def build_references():
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[0])
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[1], compress=False)
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[2])
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[3], hash_mode='md5', compress=False)
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[4])
    fast_package_file.build(os.path.join('test_dir', 'docs_v1.0_testing'), ref_list[5], hash_mode='sha256', compress=False)


ref_list = [os.path.join('test_dir', 'ref_compressed.data'), os.path.join('test_dir', 'ref_uncompressed.data'), os.path.join('test_dir', 'ref_md5_compressed.data'),
            os.path.join('test_dir', 'ref_md5_uncompressed.data'), os.path.join('test_dir', 'ref_sha256_compressed.data'), os.path.join('test_dir', 'ref_sha256_uncompressed.data')]
test_list = [ref.replace('ref', 'test') for ref in ref_list]


if __name__ == '__main__':
    unittest.main()