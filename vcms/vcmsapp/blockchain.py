import hashlib
import time
import json
from cryptography.fernet import Fernet
from vcmsapp.models import MedicalHistory

class Block:
    def __init__(self, index, previous_hash, timestamp, data, hash):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash


def calculate_hash(index, previous_hash, timestamp, data):
    value = str(index) + str(timestamp) + str(previous_hash) + str(data)
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def create_genesis_block():
    return Block(0, "0", int(time.time()), "Genesis Block", calculate_hash(0, "0", int(time.time()), "Genesis Block"))


def create_new_block(previous_block, data):
    index = previous_block.index + 1
    timestamp = int(time.time())
    hash = calculate_hash(index, previous_block.previous_hash, timestamp, data)
    return Block(index, previous_block.previous_hash, timestamp, data, hash)

class Blockchain:
    _instance = None

    def __init__(self):
        try:
            with open('vcms/encryption_key.txt', 'rb') as file:
                self.key = file.read()
        except FileNotFoundError:
            self.key = Fernet.generate_key()
            with open('vcms/encryption_key.txt', 'wb') as file:
                file.write(self.key)
        self.cipher_suite = Fernet(self.key)  # Create a cipher suite for decryption
        self.chain = []

    @classmethod
    def add_block(cls, data):
        if cls._instance is None:
            cls.load()
        encrypted_data = cls._instance.encrypt_data(data)  # Encrypt the data
        previous_block = cls._instance.chain[-1]
        new_block = create_new_block(previous_block, encrypted_data)
        cls._instance.chain.append(new_block)

    @classmethod
    def get_block_data(cls, block):
        if cls._instance is None:
            cls.load()
        encrypted_data = block.data
        decrypted_data = cls._instance.decrypt_data(encrypted_data)  # Decrypt the data
        return decrypted_data

    @classmethod
    def encrypt_data(cls, data):
        if cls._instance is None:
            cls.load()
        data_str = json.dumps(data)
        cipher_text = cls._instance.cipher_suite.encrypt(data_str.encode())
        return cipher_text

    @classmethod
    def decrypt_data(cls, cipher_text):
        if cls._instance is None:
            cls.load()
        plain_text = cls._instance.cipher_suite.decrypt(cipher_text)
        data = json.loads(plain_text.decode())
        return data
    
    def create_block_from_model(self, block_model):
        return Block(block_model.index, block_model.previous_hash, block_model.timestamp, block_model.data, block_model.hash)
    
    def validate_block(self, new_block, previous_block):
        if new_block.index != 0:  # Not a genesis block
            if previous_block.index + 1 != new_block.index:
                return False
            if previous_block.hash != new_block.previous_hash:
                return False
        if calculate_hash(new_block.index, new_block.previous_hash, new_block.timestamp, new_block.data) != new_block.hash:
            return False
        return True
    
    @classmethod
    def load(cls):
        if cls._instance is None:
            cls._instance = cls()
        cls._instance.chain = []
        blocks = MedicalHistory.objects.all().order_by('index')
        for block_model in blocks:
            block = cls._instance.create_block_from_model(block_model)
            if len(cls._instance.chain) > 0 and not cls._instance.validate_block(block, cls._instance.chain[-1]):
                raise Exception(f"Invalid block at index {block.index}")
            
            encrypted_data = block.data
            decrypted_data = cls.decrypt_data(encrypted_data)
            block.data = decrypted_data
            cls._instance.chain.append(block)
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls.load()
        return cls._instance