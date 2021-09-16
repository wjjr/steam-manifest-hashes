#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import sys

from lxml import etree
from pathlib import Path, PureWindowsPath
from urllib.request import Request, urlopen

from steam.core.manifest import DepotManifest, DepotFile


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'


def get_filenames(depot_id):
    print('Requesting filenames from steamdb.info...', end='', flush=True, file=sys.stderr)
    request = Request(f"https://steamdb.info/depot/{depot_id}/", headers={'User-Agent': USER_AGENT})
    f = urlopen(request)
    data = f.read().decode('utf-8')
    print(' OK', file=sys.stderr)

    manifest_id = etree.fromstring(data, etree.HTMLParser()).xpath('//td[text()="Manifest ID"]/following::td/text()')[0]
    files = etree.fromstring(data, etree.HTMLParser()).xpath('//table[contains(@class, "file-tree")]/tbody/tr/td[position()=1]/text()')

    hash_files = {}

    for filename in files:
        filename = str(PureWindowsPath(filename))
        hash = hashlib.sha1(filename.lower().encode()).hexdigest()
        hash_files[hash] = filename

    return hash_files, manifest_id


def get_manifest(depot_id, manifest_id):
    print('Downloading manifest from steam...', end='', flush=True, file=sys.stderr)
    request = Request(f"https://cache2-scl1.steamcontent.com/depot/{depot_id}/manifest/{manifest_id}/5", headers={'User-Agent': USER_AGENT})
    f = urlopen(request)
    data = f.read()
    print(' OK', file=sys.stderr)

    return DepotManifest(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract SHA1 hashes from steam manifest')
    parser.add_argument('-v', '--verbose', action='count', default=0, help=argparse.SUPPRESS)
    parser.add_argument('-l', '--linux', dest='linux_separators', action='store_true', help='output filenames with linux separators')
    parser.add_argument('depot_id', metavar='DEPOT_ID', type=int, help='depot id')
    parser.add_argument('manifest_id', metavar='MANIFEST_ID', type=int, help='manifest id', nargs='?')
    args = parser.parse_args()

    hash_filenames, manifest_id = get_filenames(args.depot_id)
    depot_manifest = get_manifest(args.depot_id, args.manifest_id or manifest_id)

    if args.verbose:
        for hash, filename in hash_filenames.items():
            print(f'filename_sha1="{hash}", filename="{filename}"', file=sys.stderr)

    for file_mapping in depot_manifest.payload.mappings:
        if DepotFile(depot_manifest, file_mapping).is_file:
            is_filenames_decrypted = file_mapping.sha_filename.hex() in hash_filenames
            file_sha1 = file_mapping.sha_content.hex() if file_mapping.sha_content.hex() != '0000000000000000000000000000000000000000' else 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
            file_name = hash_filenames[file_mapping.sha_filename.hex()] if is_filenames_decrypted else file_mapping.sha_filename.hex()

            if args.linux_separators:
                file_name = PureWindowsPath(file_name).as_posix()

            print('{:s} {:s}{:s}'.format(file_sha1, '*' if is_filenames_decrypted else '_', file_name))
