from web3storage import Client as Web3Client
from datetime import datetime
from zipfile import ZipFile
from pathlib import Path
from rich import print
import json
import os

# cryptography imports
import cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def load_key():
    if not Path('key.pem').is_file():
        print("[bold red]Key not found[/bold red]\nGenerating key (please wait)...")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096, # need bigger key to enc more bytes
            backend=default_backend()
        )
        with open('key.pem', 'wb') as key_file:
            key_file.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        print("[bold green]Key generated[/bold green]\nSaved to [italic]key.pem[/italic]")
    else:
        with open('key.pem', 'rb') as key_file:
            key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )
    return key

def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config

def add_to_zip(file_obj, zip_file):
    print('[bold blue]Adding ' + file_obj.name + ' to backup...[/bold blue]')
    if file_obj.is_dir():
        for f in file_obj.iterdir():
            add_to_zip(f, zip_file)
    else:
        zip_file.write(str(file_obj)) # str gets the path
        print('[grey]Added[/grey] ' + str(file_obj))

def create_zip(dirs):
    print('[bold blue]Creating backup...[/bold blue]')
    out_file = 'backup_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.zip'
    zipObj = ZipFile(out_file, 'w')
    for d in dirs:
        add_to_zip(Path(d), zipObj)
    zipObj.close()
    return out_file

def encrypt_backup(filename, key):
    print('[bold blue]Encrypting backup...[/bold blue]')
    with open(filename, 'rb') as f:
        data = f.read()
    enc = key.public_key().encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    with open('encrypted_' + filename, 'wb') as f:
        f.write(enc)
    return 'encrypted_' + filename

def upload_backup(filename, client: Web3Client):
    print('[bold blue]Uploading backup...[/bold blue]')
    cid = client.upload_file(filename)['cid']
    with open('backups.txt', 'a+') as f:
        f.write(cid + '\n')
    print('[bold green]Saved backup with CID: ' + cid + '[/bold green]')

def restore_last_backup(client: Web3Client, key):
    print('[bold blue]Restoring last backup...[/bold blue]')
    with open('backups.txt', 'r') as f:
        cid = f.readlines()[-1].strip()
    with open('last_backup.zip', 'wb') as f:
        enc = client.download_file(cid)
        f.write(key.decrypt(
            enc,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        ))
    print('[bold green]Restored backup to [italic]last_backup.zip[/italic][/bold green]')

if __name__ == '__main__':
    key = load_key()
    config = load_config()
    client = Web3Client(config['api_key'])
    if not config['paths']:
        print('[bold red]No directories specified[/bold red]\nCheck config.json')
        exit(1)
    if input('Would you like to restore the last backup or create a new one? [r/C] ').lower() == 'r':
        restore_last_backup(client, key)
        exit(0)
    filename = create_zip(config['paths'])
    encrypted_filename = encrypt_backup(filename, key)
    upload_backup(encrypted_filename, client)