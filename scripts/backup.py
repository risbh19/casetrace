"""Encrypt a Compose PostgreSQL backup, or restore into a new verification database.

Requires the backend environment (cryptography), Docker Compose, and a protected 32-byte key file.
No plaintext backup is written to disk. Restore authenticates the entire archive before executing SQL.
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryFile

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"CASETRACE1"
CHUNK = 1024 * 1024


def encrypt_stream(source, destination, key):
    nonce = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(MAGIC)
    destination.write(MAGIC + nonce + b"\0" * 16)
    while chunk := source.read(CHUNK):
        destination.write(cipher.update(chunk))
    destination.write(cipher.finalize())
    destination.seek(len(MAGIC) + 12)
    destination.write(cipher.tag)


def decrypt_stream(source, destination, key):
    if source.read(len(MAGIC)) != MAGIC:
        raise ValueError("Unrecognized archive")
    nonce, tag = source.read(12), source.read(16)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
    cipher.authenticate_additional_data(MAGIC)
    while chunk := source.read(CHUNK):
        value = cipher.update(chunk)
        if destination is not None:
            destination.write(value)
    value = cipher.finalize()
    if destination is not None:
        destination.write(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["backup", "restore-check"])
    parser.add_argument("archive", type=Path)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--compose-file", action="append", default=[])
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--project", default="casetrace")
    parser.add_argument("--database", default="casetrace_restore_check")
    args = parser.parse_args()
    key = args.key_file.read_bytes()
    if len(key) != 32:
        raise SystemExit("Use an independently generated and protected 32-byte key file")
    command = ["docker", "compose", "--env-file", args.env_file, "-p", args.project]
    for file in args.compose_file or ["compose.production.yml"]:
        command.extend(["-f", file])
    command.extend(["exec", "-T", "db"])
    if args.operation == "backup":
        # Open exclusively so a previous backup can never be overwritten.
        with args.archive.open("xb") as output:
            process = subprocess.Popen(command + ["sh", "-c", 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'], stdout=subprocess.PIPE)
            try:
                encrypt_stream(process.stdout, output, key)
                if process.wait() != 0:
                    raise RuntimeError("Database export failed; this archive is incomplete")
            finally:
                process.stdout.close()
                if process.poll() is None:
                    process.terminate()
        print("Encrypted backup created. Retain its key separately and run restore-check.")
    else:
        if not re.fullmatch(r"casetrace_restore_[a-z0-9_]+", args.database):
            raise SystemExit("Restore verification requires a new casetrace_restore_* database")
        # Authenticate a private copy, avoiding archive replacement between validation and restore.
        # This temporary file contains ciphertext only.
        with TemporaryFile() as reviewed:
            with args.archive.open("rb") as source:
                shutil.copyfileobj(source, reviewed, CHUNK)
            reviewed.seek(0)
            decrypt_stream(reviewed, None, key)
            reviewed.seek(0)
            # createdb must succeed: an existing database is never dropped or overwritten.
            subprocess.run(command + ["sh", "-c", 'exec createdb -U "$POSTGRES_USER" "$1"', "restore-check", args.database], check=True)
            process = subprocess.Popen(command + ["sh", "-c", 'exec pg_restore -U "$POSTGRES_USER" --no-owner --no-privileges --exit-on-error -d "$1"', "restore-check", args.database], stdin=subprocess.PIPE)
            try:
                decrypt_stream(reviewed, process.stdin, key)
                process.stdin.close()
                if process.wait() != 0:
                    raise RuntimeError("Restore failed; inspect the new verification database")
            finally:
                if process.poll() is None:
                    process.terminate()
        print(f"Authenticated backup restored into {args.database}; live data was not replaced.")


if __name__ == "__main__":
    main()
