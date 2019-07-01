import base64
import os
import unittest

import fast_package_file


class TestTF2RichPresenseFunctions(unittest.TestCase):
    def setUp(self):
        if 'test_dir' not in os.getcwd():
            os.chdir('test_dir')

    # tests building packages against the reference builds
    def test_build(self):
        if [ref for ref in ref_list if not os.path.exists(ref)]:
            # build references only if needed
            build_references()

        fast_package_file.build('docs_v1.0_testing', test_list[0], compress=False)
        fast_package_file.build('docs_v1.0_testing', test_list[1])
        fast_package_file.build('docs_v1.0_testing', test_list[2], hash_mode='md5', compress=False)
        fast_package_file.build('docs_v1.0_testing', test_list[3], hash_mode='md5')
        fast_package_file.build('docs_v1.0_testing', test_list[4], hash_mode='sha256', compress=False)
        fast_package_file.build('docs_v1.0_testing', test_list[5], hash_mode='sha256')

        file_data = {}
        for file in ref_list + test_list:
            with open(file, 'rb') as file_opened:
                file_data[file] = file_opened.read()

        for ref in ref_list:
            test_name = ref.replace('ref', 'test')

            try:
                test_length = len(file_data[test_name])
                ref_length = len(file_data[ref])
                self.assertGreaterEqual(test_length - ref_length, -20000)
                self.assertLessEqual(test_length - ref_length, 20000)
            except AssertionError:
                print(test_name, base64.b64encode(file_data[test_name]))
                print(ref, base64.b64encode(file_data[ref]))
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

            with open(os.path.join('docs_v1.0_testing', 'index.rst'), 'rb') as dist_file_ref:
                dist_file_ref_data = dist_file_ref.read()

                self.assertEqual(test_file_loaded.load_file('index.rst'), dist_file_ref_data)

            with open(os.path.join('docs_v1.0_testing', '_build', 'html', 'index.html'), 'rb') as dist_file_ref:
                dist_file_ref_data = dist_file_ref.read()

                self.assertEqual(test_file_loaded.load_file(r'_build\html\index.html'), dist_file_ref_data)

    # test loading a directory
    def test_load_bulk(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        with open(os.path.join('docs_v1.0_testing', '_build', 'doctrees', 'environment.pickle'), 'rb') as environment_pickle:
            environment_pickle_ref = environment_pickle.read()
        with open(os.path.join('docs_v1.0_testing', '_build', 'html', 'genindex.html'), 'rb') as genindex_html:
            genindex_html_ref = genindex_html.read()

        for test_file in test_list:
            test_file_loaded = fast_package_file.PackagedDataFile(test_file)

            self.assertEqual(test_file_loaded.load_bulk(prefix=r'_build\doctrees')[0], environment_pickle_ref)
            self.assertEqual(test_file_loaded.load_bulk(prefix=r'_build\html', postfix='.html')[0], genindex_html_ref)

    # test oneshot() and oneshot_bulk()
    def test_oneshots(self):
        if [test_file for test_file in test_list if not os.path.exists(test_file)]:
            # if running test individually
            self.test_build()

        with open(os.path.join('docs_v1.0_testing', '_build', 'doctrees', 'environment.pickle'), 'rb') as environment_pickle:
            environment_pickle_ref = environment_pickle.read()
        with open(os.path.join('docs_v1.0_testing', '_build', 'html', 'genindex.html'), 'rb') as genindex_html:
            genindex_html_ref = genindex_html.read()

        for test_file in test_list:
            self.assertEqual(fast_package_file.oneshot(test_file, r'_build\doctrees\environment.pickle'), environment_pickle_ref)
            self.assertEqual(fast_package_file.oneshot_bulk(test_file, prefix=r'_build\html', postfix='.html')[0], genindex_html_ref)

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
            with open('test_compressed.data', 'rb') as test_compressed_data:
                with open('test_compressed_bad_header.data', 'wb') as test_compressed_bad_header:
                    test_compressed_bad_header.write(test_compressed_data.read()[1:])

            fast_package_file.PackagedDataFile('test_compressed_bad_header.data')

        try:
            self.assertTrue("test_compressed_bad_header.data is corrupted or malformed (header length is " in e.exception.args[0])
        except AssertionError:
            print(e.exception.args[0])
            raise

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_compressed.data', 'rb') as test_compressed_data:
                test_compressed_data_read = test_compressed_data.read()

                with open('test_compressed_bad_json.data', 'wb') as test_compressed_bad_header:
                    test_compressed_bad_header.write(test_compressed_data_read[:100])
                    test_compressed_bad_header.write(test_compressed_data_read[120:])

            fast_package_file.PackagedDataFile('test_compressed_bad_json.data')
        self.assertEqual(e.exception.args[0], "test_compressed_bad_json.data is corrupted or malformed ('utf-8' codec can't decode byte 0x8b in position 1: invalid start byte)")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_uncompressed.data', 'rb') as test_uncompressed_data:
                test_uncompressed_data_read = test_uncompressed_data.read()

                with open('test_uncompressed_bad_json.data', 'wb') as test_uncompressed_bad_header:
                    test_uncompressed_bad_header.write(test_uncompressed_data_read[:100])
                    test_uncompressed_bad_header.write(test_uncompressed_data_read[120:])

            fast_package_file.PackagedDataFile('test_uncompressed_bad_json.data')
            
        try:
            self.assertEqual(e.exception.args[0], "test_uncompressed_bad_json.data is corrupted or malformed (couldn't decode JSON)")
        except AssertionError:
            self.assertTrue(e.exception.args[0].startswith("test_uncompressed_bad_json.data is corrupted or malformed ('utf-8' codec can't decode byte "))

        # for PackagedDataFile.load_file()
        with self.assertRaises(fast_package_file.PackageDataError) as e:
            test_compressed_data = fast_package_file.PackagedDataFile('test_compressed.data')
            test_compressed_data.load_file('a non-existent file')
        self.assertEqual(e.exception.args[0], "test_compressed.data is corrupted or malformed (file 'a non-existent file' doesn't exist in location header)")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_uncompressed.data', 'rb') as test_uncompressed_data:
                with open('test_uncompressed_bad_cstate.data', 'wb') as test_uncompressed_bad_cstate:
                    test_uncompressed_bad_cstate.write(test_uncompressed_data.read().replace(b',0,', b',2,'))

            fast_package_file.PackagedDataFile('test_uncompressed_bad_cstate.data').load_file('index.rst')
        self.assertEqual(e.exception.args[0], "test_uncompressed_bad_cstate.data is corrupted or malformed (compressed state of 'index.rst' is 2, should be 1 or 0)")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_md5_uncompressed.data', 'rb') as test_md5_uncompressed_data:
                with open('test_md5_uncompressed_bad_hash_method.data', 'wb') as test_md5_uncompressed_bad_hash_method_data:
                    test_md5_uncompressed_bad_hash_method_data.write(test_md5_uncompressed_data.read().replace(b',"md5   ', b',"mi6   '))

            fast_package_file.PackagedDataFile('test_md5_uncompressed_bad_hash_method.data').load_file('index.rst')
        self.assertEqual(e.exception.args[0], "test_md5_uncompressed_bad_hash_method.data is corrupted or malformed (hash method seems to be 'mi6   ')")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_md5_uncompressed.data', 'rb') as test_md5_uncompressed_data:
                test_md5_uncompressed_data_read = test_md5_uncompressed_data.read()

                with open('test_md5_uncompressed_bad_filedata.data', 'wb') as test_md5_uncompressed_bad_filedata_data:
                    test_md5_uncompressed_bad_filedata_data.write(test_md5_uncompressed_data_read[:3000])
                    test_md5_uncompressed_bad_filedata_data.write(test_md5_uncompressed_data_read[3500:])

            fast_package_file.PackagedDataFile('test_md5_uncompressed_bad_filedata.data').load_file('conf.py')
        self.assertTrue(e.exception.args[0].startswith("test_md5_uncompressed_bad_filedata.data is corrupted or malformed ('conf.py' hash mismatch: "))

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            with open('test_uncompressed.data', 'rb') as test_uncompressed_data:
                test_uncompressed_data_read = test_uncompressed_data.read()

                with open('test_uncompressed_bad_filedata.data', 'wb') as test_uncompressed_bad_filedata_data:
                    test_uncompressed_bad_filedata_data.write(test_uncompressed_data_read[:3000])
                    test_uncompressed_bad_filedata_data.write(test_uncompressed_data_read[3500:])

            fast_package_file.PackagedDataFile('test_uncompressed_bad_filedata.data').load_file('conf.py')
        self.assertEqual(e.exception.args[0], "test_uncompressed_bad_filedata.data is corrupted or malformed (first byte of file 'conf.py' should be 101, but was loaded as 35)")

        with self.assertRaises(fast_package_file.PackageDataError) as e:
            fast_package_file.PackagedDataFile('test_compressed.data').load_bulk(prefix='pre', postfix='post')
        self.assertEqual(e.exception.args[0], "test_compressed.data is corrupted or malformed (no file paths start with 'pre' and end with 'post')")

        for file_to_delete in ['test_compressed_bad_header.data', 'test_compressed_bad_json.data', 'test_md5_uncompressed_bad_filedata.data', 'test_md5_uncompressed_bad_hash_method.data',
                               'test_uncompressed_bad_cstate.data', 'test_uncompressed_bad_filedata.data', 'test_uncompressed_bad_json.data']:
            os.remove(file_to_delete)


# build reference package files
def build_references():
    fast_package_file.build('docs_v1.0_testing', ref_list[0], compress=False)
    fast_package_file.build('docs_v1.0_testing', ref_list[1])
    fast_package_file.build('docs_v1.0_testing', ref_list[2], hash_mode='md5', compress=False)
    fast_package_file.build('docs_v1.0_testing', ref_list[3], hash_mode='md5')
    fast_package_file.build('docs_v1.0_testing', ref_list[4], hash_mode='sha256', compress=False)
    fast_package_file.build('docs_v1.0_testing', ref_list[5], hash_mode='sha256')


ref_list = ['ref_uncompressed.data', 'ref_compressed.data', 'ref_md5_uncompressed.data', 'ref_md5_compressed.data', 'ref_sha256_uncompressed.data', 'ref_sha256_compressed.data']
test_list = [ref.replace('ref', 'test') for ref in ref_list]


if __name__ == '__main__':
    unittest.main()
