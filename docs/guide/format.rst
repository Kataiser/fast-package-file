Packaged data file format
-------------------------

Although the builder and loader for this format are implemented in Python, the format can of course be read by any languange.

	* ``0x00`` (8-byte unsigned little-endian int): Size of the file location header, in bytes, as stored in the file (i.e. after compression).
	* ``0x08`` (1-byte bool): Whether the header is compressed (not including these first 10 bytes, which are never compressed).
	* ``0x09`` (1-byte bool): Whether the file paths use crc32 encoding.
	* ``0x0A`` (UTF-8 string): The file location header, as JSON.
	* The rest is file data, placed end-to-end.
	
File location header (JSON)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

	{"folder\\file1.txt":
		[file location, relative to the end of the entire header (int),
		 file size, after compression if enabled (int),
		 file is compressed (bool),
		 first byte of file (int),
		 last byte of file (int)],
	"folder\\file2.txt": [...], ...}

.. note::
	This example is multi-line for readability, but the actual format has no newlines.
	
.. note::
	File paths are stored as actual double backslashes (``\\``). Python's JSON loader handles this automatically, make sure yours does or reformat the string.
	
.. note::
	If using crc32 file paths, they are stored as strings of integers.