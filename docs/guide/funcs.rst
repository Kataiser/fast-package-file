Function reference
------------------

Building packages
^^^^^^^^^^^^^^^^^

.. py:module:: fast_package_file
.. py:currentmodule:: fast_package_file
.. autofunction:: build

Getting data out of packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. py:currentmodule:: fast_package_file.PackagedDataFile
.. autofunction:: __init__
.. autofunction:: load_file
.. autofunction:: load_bulk

Helpers
^^^^^^^

.. py:currentmodule:: fast_package_file
.. autofunction:: oneshot
.. autofunction:: oneshot_bulk

.. py:currentmodule:: fast_package_file.PackagedDataFile
.. py:attribute:: file_data

    A dictionary containing the file location data.
	
    :type: :py:class:`dict`: ``{'path': (offset, length, compressed (1 or 0), first byte, last byte)}``
.. autofunction:: __repr__

.. py:currentmodule:: fast_package_file
.. autoexception:: PackageDataError