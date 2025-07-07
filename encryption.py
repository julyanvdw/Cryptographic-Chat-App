
import hashlib
import nacl.bindings
import nacl.public
import hmac
import time
import math
import secrets
import struct
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey


# CONSTANTS
LABELMAC1 = b'mac1----'
CONSTRUCTION = b'Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s'
IDENTIFIER = b'WireGuard v1 zx2c4 Jason@zx2c4.com'
# Raw server public key (as a 32-byte WireGuard-style static key)
SERVER_STATIC_PUBLIC_KEY = b'f,^\xc0Cb\xf3\x937\xbf\x11\x14"\xed\x13\x0b\x9f\xe7\xaf;\x94\xb0p\x13\xe1\x94\xdd\x85\xcf\x01\x0bC'
Q = b'\x00' * 32
# SERVER_STATIC_PUBLIC_KEY=b'f,^\xc0Cb\xf3\x937\xbf\x11\x14"\xed\x13\x0b\x9f\xe7\xaf;\x94\xb0p\x13\xe1\x94\xdd\x85\xcf\x01\x0bC'

# AUX FUNCTIONS 

def Hash(input):
    # Use hashlib to hash an input according to blake2s
    return hashlib.blake2s(input, digest_size=32).digest()

def MixHash(input1, input2):
    # Returns concatenated Hash()
    return Hash(input1 + input2)

def MAC(key, input):
    # Computes MAC - checks authenticity of message
    return hashlib.blake2s(input, key=key, digest_size=16).digest()

def DH(private_key, public_key): 
    # Does a Diffe-Hellman according to the WireGuard specification (Curve25519). Produces a share key
    return nacl.bindings.crypto_scalarmult(private_key, public_key)

def DH_Generate():
    # Generates a new Diffie-Hellman keypair according to the WireGuard specification (Curve25519)
    private_key = nacl.public.PrivateKey.generate()
    public_key = private_key.public_key
    return private_key.encode(), public_key.encode()

def HMAC(key, data):
    # Computes HMAC using blake2s
    return hmac.new(key, data, hashlib.blake2s).digest()

def Kdf1(key, input):
    # Derives the first key using HMAC() as per WireGuard spec. 
    tau0 = HMAC(key, input)
    tau1 = HMAC(tau0, b'\x01')
    return tau1

def Kdf2(key, input):
    # Derives the second key using HMAC() as per WireGuard spec.
    tau0 = HMAC(key, input)
    tau1 = HMAC(tau0, b'\x01')
    tau2 = HMAC(tau0, tau1 + b'\x02')
    return tau1, tau2

def Kdf3(key, input):
    # Derives the third key using HMAC() as per WireGuard spec.
    tau0 = HMAC(key, input)
    tau1 = HMAC(tau0, b'\x01')
    tau2 = HMAC(tau0, tau1 + b'\x02')
    tau3 = HMAC(tau0, tau2 + b'\x03')
    return tau1, tau2, tau3

def AEAD_encrypt(key, counter, plaintext, authtext):
    # Encrypts the data with a key. Only people with the key can decrypt the data again. 
    # Also checks if the message is authentic
    return nacl.bindings.crypto_aead_chacha20poly1305_ietf_encrypt(plaintext, authtext, counter, key)

def AEAD_decrypt(key, counter, ciphertext, authtext):
    # Decrypts the data with a key. Also checks that the message is authentic. 
    return nacl.bindings.crypto_aead_chacha20poly1305_ietf_decrypt(ciphertext, authtext, counter, key)

def Timestamp(unix_time=None):
    # Get Unix time
    if unix_time is None:
        utc_time = time.time()
    else:
        utc_time = unix_time
    
    
    # Constants
    LEAP_SECONDS_OFFSET = 10  # This matches the expected output
    TAI64_EPOCH_OFFSET = (1 << 62)
    
    # Calculate TAI64 label
    tai_seconds = math.floor(utc_time + LEAP_SECONDS_OFFSET)
    tai64_label = TAI64_EPOCH_OFFSET + tai_seconds
    
    # Calculate nanoseconds
    fractional_part = utc_time - math.floor(utc_time)
    nanoseconds = int(fractional_part * 1e6)  # Use microseconds precision
    
    try:
        # Pack as big-endian 8-byte unsigned long and 4-byte unsigned int
        result = struct.pack('>QI', tai64_label, nanoseconds)
        return result
    except struct.error as e:
        print(f"Error packing TAI64N timestamp: {e}")
        return None
    
# WIREGUARD PROCEDURES

# MAC 1 and 2 - Section 5.4.4 

def get_MAC1(server_public_key, msg):
    # Generates MAC1 according to WireGuard spec. Used for checking message integrity
    return MAC(MixHash(LABELMAC1, server_public_key), msg)

def get_MAC2():
    return b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

# Initiation Message - Section 5.4.2

def get_Initiation_Message(server_public_key_static, client_private_key_static, client_private_key_ephemeral=None, client_public_key_ephemeral=None, timestamp_input=None, sender_index=None):
    # Implementation of an initiation handshake as per WireGuard specs. 
    # First get the hash and the chain key
    chain_key = Hash(CONSTRUCTION)
    hash = MixHash(chain_key, IDENTIFIER)
    hash = MixHash(hash, server_public_key_static)

    # Generate ephemeral private and public keys (note: for unit testing, we allow for test-injecting keys, hence the if-statement)
    if client_private_key_ephemeral is None or client_public_key_ephemeral is None:
        client_private_key_ephemeral, client_public_key_ephemeral = DH_Generate()

    chain_key = Kdf1(chain_key, client_public_key_ephemeral)
    msg_ephemeral = client_public_key_ephemeral
    hash = MixHash(hash, msg_ephemeral)

    # Perform a DH() to get a common key
    common_key = DH(client_private_key_ephemeral, server_public_key_static)
    chain_key, key1 = Kdf2(chain_key, common_key)

    # Derrive client public key
    client_public_key_static = nacl.public.PrivateKey(client_private_key_static).public_key.encode()
    
    # Encrypt static public key
    msg_static_encrypted = AEAD_encrypt(key1, b'\x00' * 12, client_public_key_static, hash)
    hash = MixHash(hash, msg_static_encrypted)

    # Perform DH() to get new common key (the other way around)
    common_key = DH(client_private_key_static, server_public_key_static)
    chain_key, key2 = Kdf2(chain_key, common_key)

    # Encrypt the timestamp
    if timestamp_input is None:
        timestamp = Timestamp()
    else:
        timestamp = Timestamp(timestamp_input)

    encrypted_timestamp = AEAD_encrypt(key2, b'\x00' * 12, timestamp, hash)

    hash = MixHash(hash, encrypted_timestamp)

    # CONSTRUCTING THE FINAL MESSAGE
    msg_type = b'\x01'
    reserved = b'\x00' * 3
    
    if sender_index is None: 
        sender_index = secrets.token_bytes(4)
    else:
        sender_index = sender_index.to_bytes(4, byteorder='little')

    # constructs message according to protocol definition
    msg = (
        msg_type + 
        reserved + 
        sender_index + 
        client_public_key_ephemeral + 
        msg_static_encrypted + 
        encrypted_timestamp
        )
    
    mac1 = get_MAC1(server_public_key_static, msg)
    mac2 = get_MAC2()

    final_message = (
        msg_type + 
        reserved + 
        sender_index + 
        client_public_key_ephemeral + 
        msg_static_encrypted + 
        encrypted_timestamp + 
        mac1 + 
        mac2
        )
    
    # Define a ds to keep track of handshake throughout the process
    handshake_info = {
        'chain_key': chain_key, 
        'hash' : hash,
        'client_index': sender_index,
        'server_index': None,
        'client_private_key_ephemeral': client_private_key_ephemeral
    }
        
    return handshake_info, final_message, msg

# Response to initiation - Section 5.4.3

def parse_Server_Response(response_message: bytes, handshake_info: dict, client_private_key_static: bytes, testing:bool = False):
    """
      This method parses the response from the server during the intiation handshake according to WireGuard Spec.
      Also divides the received packet up into sub-fields (could be useful later)
      returns the chain_key for following messages
    """
    # obtaining relevent data from handshake_info
    hash = handshake_info['hash']
    chain_key = handshake_info['chain_key']
    client_private_key_ephemeral = handshake_info['client_private_key_ephemeral']

    # Dividing into sub-fields
    msg_type = response_message[0] #first byte indicates type
    reserved = response_message[1:4]
    sender = response_message[4:8]
    receiver = response_message[8:12]
    server_public_key_ephemeral = response_message[12:44]
    empty_encrypted = response_message[44:60]
    mac1 = response_message[60:76]
    mac2 = response_message[76:]

    # Perform decryp operations
    chain_key = Kdf1(chain_key, server_public_key_ephemeral)
    msg_ephemeral = server_public_key_ephemeral
    hash = MixHash(hash, msg_ephemeral)

    # Perform DH on ephemeral keys
    common_key = DH(client_private_key_ephemeral, server_public_key_ephemeral)
    chain_key = Kdf1(chain_key, common_key)

    # Perform DH on ephemeral key and static private
    common_key = DH(client_private_key_static, server_public_key_ephemeral)
    chain_key = Kdf1(chain_key, common_key)

    chain_key, tmp, key3 = Kdf3(chain_key, Q)
    hash = MixHash(hash, tmp)

    if testing: 
        return hash, chain_key, tmp, key3

    # Perform the decrypt
    empty_decrypted = AEAD_decrypt(key3, b'\x00'*12, empty_encrypted, hash)

    hash = MixHash(hash, empty_decrypted)

    # update handshake_info
    handshake_info['server_index'] = sender 

    return chain_key, handshake_info

# Transport Key Derivation - Section 5.4.5

def derive_transport_keys(chain_key):
    """
    This method obtains keys used in transport messages after the initial handshake
    """
    T_client_sending, T_client_receiving = Kdf2(chain_key, b'')

    transport_keys = {
        'T_client_sending': T_client_sending,
        'T_client_receiving': T_client_receiving,
        'N_client_sending': 0,
        'N_client_receiving': 0
    }

    return transport_keys

#  Transport Data Messages - Section 5.4.6

def construct_transport_message(transport_keys: dict, handshake_info: dict, payload): 
    """
    This method constructs a transport message (packet) according to WireGuard spec
    returns the packet (with encrypted payload + header info) and updated handshake_info (used in the session)
    """
    
    msg_type = b'\x04' #This message type means 'send'
    reserved = b'\x00' * 3
    reciever_index = handshake_info['server_index']
    counter = transport_keys['N_client_sending'].to_bytes(8, 'little')
    nonce = b'\x00\x00\x00\x00' + counter

    # perform encryption on payload
    encrypted_payload = AEAD_encrypt(transport_keys['T_client_sending'],
                                    nonce,
                                    payload,
                                    b''
                                    )
    
    # construct the transport message
    transport_message = (msg_type + 
                         reserved + 
                         reciever_index + 
                         counter + 
                         encrypted_payload
                         )

    # update the counter
    transport_keys['N_client_sending'] += 1

    return transport_keys, transport_message

def consume_transport_message(input_data, transport_keys: dict):
    """
    This method accepts packets from the server and consumes and decrypts them
    """

    # Split packet into different components
    msg_type = input_data[0]
    reserved = input_data[1:4]
    client_index = input_data[4: 8]
    counter_bytes = input_data[8:16]
    encrypted_data = input_data[16:]

    counter = int.from_bytes(counter_bytes, 'little')
    nonce = b'\x00\x00\x00\x00' + counter_bytes

    # perform the decrypt 
    decrypted_data = AEAD_decrypt(transport_keys['T_client_receiving'], 
                                  nonce,
                                  encrypted_data,
                                  b'') 
    
    # increment the counter
    if counter > transport_keys['N_client_receiving']:
        transport_keys['N_client_receiving'] = counter

    return decrypted_data, transport_keys