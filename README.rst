.. image:: https://github.com/hille721/bits3/workflows/build/badge.svg
    :alt: Built Status
    :target: https://github.com/hille721/bits3/actions?query=workflow%3Abuild

=====
bits3
=====


Upload Backintime snapshots to AWS S3.


Description
===========

`Back In Time <https://github.com/bit-team/backintime>`_ is a simple backup tool for Linux, which saves your backups as normal directories on external disks or remote servers.
With **bits3** you can save Back In Time backups as archive on AWS S3.

The Back In Time backup directory will be packed as a tar, encrypted with a password via the Linux tool `GnuPG <https://gnupg.org>`_ and uploaded to AWS S3 via the official AWS SDK for Python (`boto3 <https://boto3.amazonaws.com>`_).

This process will take a few hours for large backup directories. Thus **bits3** is not for daily backup purpose, rather for creating emergency backups every few months, which can be used, if all other backups are lost. 

Installation
============
Python3.6 or greate is required.

.. code-block::

    pip install bits3


Usage
=====

AWS Config
**********
You have to create a new AWS bucket first. For each backup directory you have to use a dedicated bucket!

The handling of the AWS credential is the same as in the official AWS CLI. You can use environment variables or a credentials file. Check the official documentation for more information (`<https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html>`_).


Run bits3
*********
.. code-block::

   bits3 --progress --bucket <AWS_BUCKET_NAME> --secret <PASWORD_FOR_ENCRYPTION> <BACKINTIME_BACKUP_DIR>


`<AWS_BUCKET_NAME>` and `<PASWORD_FOR_ENCRYPTION>` can also be provided via environment variables:

.. code-block::

   export BITS3_BUCKET=<AWS_BUCKET_NAME>
   export BITS3_SECRET=<PASWORD_FOR_ENCRYPTION>
   bits3 <BACKINTIME_BACKUP_DIR>


Help
****
There are some more options avaialbe, check the help to get more information:

.. code-block:: bash

    bits3 --help


All the options can also be defined as environment variables in the format `BITS3_OPTIONNAME`
