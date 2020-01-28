#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import sys

from pathlib import Path, PureWindowsPath
from urllib.request import Request, urlopen

from steam.core.manifest import DepotManifest, DepotFile


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'


def get_filenames(depot_id):
    print('Requesting filenames from steamdb.info...', end='', flush=True, file=sys.stderr)
    request = Request('https://steamdb.info/depot/%s/' % (depot_id), headers={'User-Agent': USER_AGENT})
    f = urlopen(request)
    data = f.read().decode('utf-8')
    print(' OK', file=sys.stderr)

    match = re.search('(?<=ProcessDepotRawFiles\(JSON\.parse\(\')(.*)(?=\'\)\))', data)

    if match:
        depot_files_json = match.group(0)
        depot_files = json.loads(depot_files_json)
        files = list(depot_files.keys())

        hash_files = {}

        for filename in files:
            filename = str(PureWindowsPath(filename))
            hash = hashlib.sha1(filename.lower().encode()).hexdigest()
            hash_files[hash] = filename

        return hash_files
    else:
        return {}


def get_manifest(depot_id, manifest_id):
    print('Downloading manifest from steam...', end='', flush=True, file=sys.stderr)
    request = Request('https://cache13-lhr1.steamcontent.com/depot/%s/manifest/%s/5' % (depot_id, manifest_id), headers={'User-Agent': USER_AGENT})
    f = urlopen(request)
    data = f.read()
    print(' OK', file=sys.stderr)

    return DepotManifest(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract SHA1 hashes from steam manifest')
    parser.add_argument('-v', '--verbose', action='count', default=0, help=argparse.SUPPRESS)
    parser.add_argument('-l', '--linux', dest='linux_separators', action='store_true', help='output filenames with linux separators')
    parser.add_argument('depot_id', metavar='DEPOT_ID', type=int, help='depot id')
    parser.add_argument('manifest_id', metavar='MANIFEST_ID', type=int, help='manifest id')
    args = parser.parse_args()

    depot_manifest = get_manifest(args.depot_id, args.manifest_id)
    hash_filenames = get_filenames(args.depot_id)

    if args.verbose:
        for hash, filename in hash_filenames.items():
            print(hash, filename)

    for file_mapping in depot_manifest.payload.mappings:
        if DepotFile(depot_manifest, file_mapping).is_file:
            file_sha1 = file_mapping.sha_content.hex() if file_mapping.sha_content.hex() != '0000000000000000000000000000000000000000' else 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
            file_name = hash_filenames[file_mapping.sha_filename.hex()] if file_mapping.sha_filename.hex() in hash_filenames else file_mapping.sha_filename.hex()
            is_filenames_decrypted = file_mapping.sha_filename.hex() in hash_filenames

            if args.linux_separators:
                file_name = PureWindowsPath(file_name).as_posix()

            print('%s %c%s' % (file_sha1, '*' if is_filenames_decrypted else '_', file_name))
