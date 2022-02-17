from web3storage import Client as Web3Client
from Crypto.PublicKey import RSA
from datetime import datetime
from zipfile import ZipFile
from pathlib import Path
from rich import print
import json
import os

def load_key():
    if not Path('key.rsa').is_file():
        print("[bold red]Key not found[/bold red]\nGenerating key...")
        key = RSA.generate(4096)
        with open('key.rsa', 'wb') as key_file:
            key_file.write(key.exportKey())
        print("[bold green]Key generated[/bold green]\nSaved to [italic]key.rsa[/italic]")
    else:
        with open('key.rsa', 'rb') as key_file:
            key = RSA.importKey(key_file.read())
    return key

def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return config

def create_zip(dirs):
    print('[bold blue]Creating backup...[/bold blue]')
    out_file = 'backup_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.zip'
    zipObj = ZipFile(out_file, 'w')
    for dirn in dirs:
        fileObj = Path(dirn)
        if fileObj.is_dir():
            for child in fileObj.iterdir():
                if child.is_dir():
                    continue
                zipObj.write(child.read_bytes(), child.name)
                print('[grey]Added[/grey] ' + child.name)
        else:
            zipObj.write(dirn.read_bytes(), dirn.name)
            print('[grey]Added[/grey] ' + dirn.name)
    zipObj.close()
    return out_file

def encrypt_backup(filename, key):
    print('[bold blue]Encrypting backup...[/bold blue]')
    with open(filename, 'rb') as f:
        data = f.read()
    enc = key.encrypt(data, 64)[0]
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
        f.write(key.decrypt(enc))
    print('[bold green]Restored backup[/bold green]')

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