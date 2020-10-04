
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.client import ClientError
from botocore.exceptions import NoCredentialsError

from .utils import ProgressPercentage

### logging stuff
logger = logging.getLogger('bits3')


def get_inputdir(backupdir):
    '''
    Get last backup directory.

    Args:
        backupdir (str): backuplocation of Backintime

    Returns:
        inputdir (Path): Path to last backup
    '''

    found = False
    for root, dirs, files  in os.walk(backupdir):
        if 'last_snapshot' in dirs:
            found = True
            break

    if not found:
        logger.error(f'It seems, that {backupdir} is not a Backintime directory.')
        return False

    inputdir = Path(root) / 'last_snapshot'
    if not inputdir.is_symlink():
        logger.error(f'It seems, that {backupdir} is not a Backintime directory.')
        return False
    inputdir = inputdir.resolve()

    return inputdir


def tar_and_encrypt(inputdir, secret, gpgcmd='gpg'):
    '''
    Pack inputdir in tar and directly encrypt it with GPG.
    No intermediate tar will be created, it will be directly streamed to gpg command.

    Deycrypting and untar can easily done via command line:
        `gpg -d test.tar.gpg | tar -xvf -`

    Args:
        inputdir (str | Path): inputdir as string or Path object
        secret (str): passphrase used for encryption
        gpcmd (str, optional): GPG command to use
    '''

    inputdir = Path(inputdir)
    outputfile = Path(f'{inputdir.absolute()}.tar.gpg')
    os.chdir(inputdir.parent)

    cmd = [gpgcmd, '-c', '--cipher-alg', 'AES256', '--batch', '--passphrase', secret]

    logger.info(f'Creation of {outputfile.name} in progress...')
    start = time.time()
    with open(outputfile, 'wb') as output:
        encrypt_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.PIPE)

        tar = tarfile.open(fileobj=encrypt_process.stdin, mode='w|')
        tar.add(inputdir.name)
        tar.close()
        _, stderr = encrypt_process.communicate()
    end = time.time()

    rc = encrypt_process.returncode
    if rc != 0:
        error = f'Calling gpg failed with return code {rc}: {stderr}'
        logger.error(error)
        return False

    logger.info(f'{outputfile} sucessfully created in {(end-start)/60.:.2f} min.')

    return outputfile


def initialize_bucket(bucketname):
    '''
    Initialize boto3 Bucket object and check if bucket really exists.

    Args:
        bucketname (str): name of bucket
    '''

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)

    try:
        s3.meta.client.head_bucket(Bucket=bucket.name)
    except NoCredentialsError:
        logger.error('No AWS credentials available')
        return False
    except ClientError:
        logger.error(f'The bucket {bucket.name} does not exist or you have no access.')
        return False

    return bucket


def check_if_upload_necessary(bucket, days=90):
    '''
    Check date of last upload.
    If date is not at least ``days`` old False will be returned.

    Args:
        bucket (boto3 Bucket object): S3 bucket to use
        days (int, optional): days between uploads (default: 90)
    '''

    now = datetime.now(timezone.utc)
    last_upload = None
    for obj in bucket.objects.all():
        if not last_upload:
            last_upload = obj.last_modified
            continue
        if obj.last_modified > last_upload:
            last_upload = obj.last_modified

    # bucket is empty
    if not last_upload:
        return True

    # check if last upload was before `days` days
    last_upload_intervall = now - last_upload
    if (last_upload_intervall).days > days:
        return True

    logger.info(f'Last backup was only {last_upload_intervall.days} days ago. Nothing to do.')
    return False


def upload_to_aws(local_file, bucket, storageclass='STANDARD_IA', progress=False):
    '''
    Upload a local file to AWS S3 storage.

    Args:
        local_file (Path object): local file to upload
        bucket (boto3 Bucket object): S3 bucket to use
        storageclass (str, optional): storage class to use (default: 'STANDARD_IA')
        progress (bool): print percentage progress output
    '''

    logger.info(f'Upload of {local_file.name} in progress...')
    if progress:
        callback = ProgressPercentage(str(local_file))
    else:
        callback = None
    try:
        start = time.time()
        bucket.upload_file(Filename=str(local_file),
                       Key=local_file.name,
                       ExtraArgs = {
                            'StorageClass': storageclass
                       },
                       Callback=callback
                       )
        end = time.time()
        if progress:
            sys.stdout.write('\r')
        logger.info(f'{local_file.name} was successfully uploaded in {(end-start)/60.:.2f} min.')
        return True
    except FileNotFoundError:
        logger.error(f'The file {local_file} was not found')
        return False
    except S3UploadFailedError as exc:
        logger.error(f'Upload failed: {str(exc)}')
        return False


def delete_old_uploads(bucket, keep=1):
    '''
    Delete old upload.

    Args:
        bucket (boto3 Bucket object): S3 bucket to use
        keep (int, optional): how many uploads to keep (default: 1)
    '''

    obj_list = list(bucket.objects.all())
    if len(obj_list) <= keep:
        # nothing to do if lees than `keep` objects in bucket
        return True

    obj_date_map = {obj.last_modified:obj for obj in obj_list}

    objs_to_delete = sorted(list(obj_date_map.keys()))[:-keep]
    for obj in objs_to_delete:
        response = obj_date_map[obj].delete()
        if response['ResponseMetadata']['HTTPStatusCode'] == 204:
            logger.info(f'Successfully deleted old backup {obj_date_map[obj].key}')

    return True



def bits3_cycle(backupdir, secret, bucketname,
                gpgcmd='gpg', storageclass='STANDARD_IA',
                uploadintervall=90, keep=1, progress=False):
    '''
    Main function of bits3
    '''

    # check S3 connection and if bucketname really exists
    bucket =  initialize_bucket(bucketname)
    if not bucket:
        return False

    # check if last upload was before DAYS days
    if not check_if_upload_necessary(bucket, days=uploadintervall):
        return False


    # get last backup
    inputdir = get_inputdir(backupdir)
    if not inputdir:
        return False

    # create encrypted tar
    outputfile = tar_and_encrypt(inputdir, secret, gpgcmd)
    if not outputfile:
        return False

    # upload to aws
    upload = upload_to_aws(outputfile, bucket, storageclass, progress=progress)

    if upload:        
        outputfile.unlink()
        delete_old_uploads(bucket, keep=keep)
        return True
    return False
