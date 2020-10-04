import logging

import click

from .core import bits3_cycle

@click.command()
@click.argument('backupdir', type=click.Path(exists=True, readable=True))
@click.option('--bucket', help='AWS S3 bucket name to store the data.', required=True)
@click.option('--secret', help='Password to use for encryption', required=True)
@click.option('--uploadintervall', type=int, help='How often upload a new snapshot in days',
              default=90, show_default=True)
@click.option('--keep', type=int, help='How many snapshot should be kept.',
              default=1, show_default=True)
@click.option('--storageclass', help='AWS S3 storage class to use',
              default='STANDARD_IA', show_default=True,
              type=click.Choice(['STANDARD', 'STANDARD_IA', 'GLACIER', 'DEEP_ARCHIVE'], case_sensitive=False))
@click.option('--progress/--no-progress', help='Print progress to stdout during S3 upload',
              type=bool, default=False, show_default=True)
@click.option('--gpgcmd', help='Path to GPG executable.',
              default='gpg', show_default=True)
@click.option('--loglevel', help='Loglevel of the application.',
              default='INFO', show_default=True,
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False))
@click.version_option()
def cli(backupdir, bucket, secret, uploadintervall,
        keep, storageclass, progress, gpgcmd, loglevel):
    '''
    Upload last snapshot of a Backintime backup to AWS S3

    BACKUPDIR: Path to Backintime backup directory
    '''

    logging.basicConfig(level=loglevel)
    bits3_cycle(backupdir=backupdir, secret=secret, bucketname=bucket,
                gpgcmd=gpgcmd, storageclass=storageclass,
                uploadintervall=uploadintervall, keep=keep,
		progress=progress)


def run():
    cli(auto_envvar_prefix='BITS3')
