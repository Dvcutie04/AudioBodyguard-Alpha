#!/usr/bin/env python3
import socket, struct, os, sys, hashlib
import rsa as rsa_lib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

IP, PORT = '10.10.30.77', 5555
KEY = os.path.expanduser('~/Documents/adbkey')
KEYS = {'up': 24, 'down': 25, 'mute': 164, 'power': 26, 'home': 3, 'back': 4, 'ok': 23, 'play': 85}

CNXN, AUTH, OPEN, OKAY, CLSE = 0x4e584e43, 0x48545541, 0x4e45504f, 0x59414b4f, 0x45534c43
AUTH_SIG, AUTH_RSAPUB = 2, 3
VERSION, MAXDATA = 0x01000001, 4096

def gen_keys():
    print('Generating RSA keypair...')
    key = rsa.generate_private_key(65537, 2048, default_backend())
    with open(KEY, 'wb') as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    pub = key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    with open(KEY + '.pub', 'wb') as f:
        f.write(pub + b' adbkey@ashell\n')

def load_rsa_key():
    if not os.path.exists(KEY):
        gen_keys()
    with open(KEY, 'rb') as f:
        return rsa_lib.PrivateKey.load_pkcs1(f.read())

def pack(cmd, arg0, arg1, data=b''):
    if isinstance(data, str):
        data = data.encode() + b'\x00'
    return struct.pack('<6I', cmd, arg0, arg1, len(data), sum(data) & 0xffffffff, cmd ^ 0xffffffff) + data

def recv_msg(sock):
    h = b''
    while len(h) < 24:
        c = sock.recv(24 - len(h))
        if not c:
            raise ConnectionError('closed')
        h += c
    cmd, a0, a1, n, _, _ = struct.unpack('<6I', h)
    d = b''
    while len(d) < n:
        c = sock.recv(n - len(d))
        if not c:
            raise ConnectionError('closed mid-payload')
        d += c
    return cmd, a0, a1, d

def send_key(keycode):
    key = load_rsa_key()
    sock = socket.socket()
    sock.settimeout(60)
    sock.connect((IP, PORT))
    sock.sendall(pack(CNXN, VERSION, MAXDATA, b'host::ashell\x00'))
    cmd, _, _, data = recv_msg(sock)
    if cmd == AUTH:
        sig = rsa_lib.sign(data, key, 'SHA-1')
        sock.sendall(pack(AUTH, AUTH_SIG, 0, sig))
        cmd, _, _, _ = recv_msg(sock)
        if cmd == AUTH:
            with open(KEY + '.pub', 'rb') as f:
                pub = f.read()
            sock.sendall(pack(AUTH, AUTH_RSAPUB, 0, pub + b'\x00'))
            print('>>> Check TV NOW - tap ALLOW <<<')
            cmd, _, _, _ = recv_msg(sock)
    if cmd != CNXN:
        raise RuntimeError(f'Handshake failed: 0x{cmd:08x}')
    sock.sendall(pack(OPEN, 1, 0, f'shell:input keyevent {keycode}\x00'))
    cmd, _, remote_id, _ = recv_msg(sock)
    if cmd != OKAY:
        raise RuntimeError(f'OPEN rejected: 0x{cmd:08x}')
    sock.sendall(pack(CLSE, 1, remote_id))
    sock.close()
    print(f'Sent keyevent {keycode}')

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'up'
    if arg not in KEYS:
        print(f'Usage: python3 tv.py [{"|".join(KEYS)}]')
        sys.exit(1)
    send_key(KEYS[arg])
