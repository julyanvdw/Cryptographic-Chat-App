import encryption
import socket

class EncryptionManager:

    #Init method sets the encryption manager up with relevant information
    #Sets testing variables to None
    #Calls the handshake initiation function


    def __init__(self, server_public_key: bytes, client_private_key: bytes, sock: socket):
        self.server_public_key = server_public_key
        self.client_private_key = client_private_key
        self.sock = sock

        # Handshake and transport state
        self.handshake_info = None
        self.transport_keys = None
        self.establish_encryption()

    # Calls get_Initiation_Message and sends it to the server. 
    # Proceeds to obtain further details via parsing a server response (parse_Server_Response)

    def establish_encryption(self):
        handshake_info, init_msg, _ = encryption.get_Initiation_Message(
                self.server_public_key,
                self.client_private_key
        )
        self.sock.send(init_msg)
        resp, _ = self.sock.recvfrom(4096)

        chain_key, handshake_info = encryption.parse_Server_Response(
                response_message=resp,
                handshake_info=handshake_info,
                client_private_key_static=self.client_private_key,
                testing=False
        )

        self.handshake_info = handshake_info
        self.transport_keys = encryption.derive_transport_keys(chain_key)
        print("Encryption established")

    # Encrypts given data to send across the network 
    # Abstracts encryption procedure

    def encrypt(self, payload: bytes) -> bytes:
        if self.transport_keys is None or self.handshake_info is None:
            raise RuntimeError("Handshake not completed") 

        self.transport_keys, encrypted_msg = encryption.construct_transport_message(
            transport_keys=self.transport_keys,
            handshake_info=self.handshake_info,
            payload=payload
        )
        return encrypted_msg

    # Decrypts given data recevied from the network
    # Abstracts decryption procedure

    def decrypt(self, encrypted_msg: bytes) -> bytes:
        if self.transport_keys is None:
            raise RuntimeError("Transport keys not set.")

        plaintext, self.transport_keys = encryption.consume_transport_message(
            encrypted_msg,
            self.transport_keys
        )
        return plaintext
