#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner API Communication Layer

This module handles all HTTP communication, encryption, and decryption
for Mitsubishi MAC-577IF-2E devices.
"""

import base64
import requests
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from typing import Optional

# Constants from the working implementation
KEY_SIZE = 16
STATIC_KEY = "unregistered"


class MitsubishiAPI:
    """Handles all API communication with Mitsubishi AC devices"""
    
    def __init__(self, device_ip: str, encryption_key: str = STATIC_KEY):
        self.device_ip = device_ip
        self.encryption_key = encryption_key
        self.session = requests.Session()
        
    def get_crypto_key(self):
        """Get the crypto key, same as TypeScript implementation"""
        buffer = bytearray(KEY_SIZE)
        key_bytes = self.encryption_key.encode('utf-8')
        buffer[:len(key_bytes)] = key_bytes
        return bytes(buffer)

    def encrypt_payload(self, payload: str) -> str:
        """Encrypt payload using same method as TypeScript implementation"""
        # Generate random IV
        iv = get_random_bytes(KEY_SIZE)
        key = self.get_crypto_key()
        
        # Encrypt using AES CBC with zero padding
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Zero pad the payload to multiple of 16 bytes
        payload_bytes = payload.encode('utf-8')
        padding_length = KEY_SIZE - (len(payload_bytes) % KEY_SIZE)
        if padding_length == KEY_SIZE:
            padding_length = 0
        padded_payload = payload_bytes + b'\x00' * padding_length
        
        encrypted = cipher.encrypt(padded_payload)
        
        # TypeScript approach: IV as hex + encrypted as hex, then base64 encode the combined hex
        iv_hex = iv.hex()
        encrypted_hex = encrypted.hex()
        combined_hex = iv_hex + encrypted_hex
        combined_bytes = bytes.fromhex(combined_hex)
        return base64.b64encode(combined_bytes).decode('utf-8')

    def decrypt_payload(self, payload: str, debug: bool = False) -> Optional[str]:
        """Decrypt payload following TypeScript implementation exactly"""
        try:
            # Convert base64 to hex string
            hex_buffer = base64.b64decode(payload).hex()
            
            if debug:
                print(f"[DEBUG] Base64 payload length: {len(payload)}")
                print(f"[DEBUG] Hex buffer length: {len(hex_buffer)}")
            
            # Extract IV from first 2 * KEY_SIZE hex characters
            iv_hex = hex_buffer[:2 * KEY_SIZE]
            iv = bytes.fromhex(iv_hex)
            
            if debug:
                print(f"[DEBUG] IV: {iv.hex()}")
            
            key = self.get_crypto_key()
            
            # Extract the encrypted portion
            encrypted_hex = hex_buffer[2 * KEY_SIZE:]
            encrypted_data = bytes.fromhex(encrypted_hex)
            
            if debug:
                print(f"[DEBUG] Encrypted data length: {len(encrypted_data)}")
                print(f"[DEBUG] Encrypted data (first 64 bytes): {encrypted_data[:64].hex()}")
            
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_data)
            
            if debug:
                print(f"[DEBUG] Decrypted raw length: {len(decrypted)}")
                print(f"[DEBUG] Decrypted raw (first 64 bytes): {decrypted[:64]}")
                print(f"[DEBUG] Decrypted raw (last 64 bytes): {decrypted[-64:]}")
            
            # Remove zero padding
            decrypted_clean = decrypted.rstrip(b'\x00')
            
            if debug:
                print(f"[DEBUG] After padding removal length: {len(decrypted_clean)}")
                print(f"[DEBUG] Non-zero bytes at end: {decrypted_clean[-20:]}")
            
            # Try to decode as UTF-8
            try:
                result = decrypted_clean.decode('utf-8')
                return result
            except UnicodeDecodeError as ude:
                if debug:
                    print(f"[DEBUG] UTF-8 decode error at position {ude.start}: {ude.reason}")
                    print(f"[DEBUG] Problematic bytes: {decrypted_clean[max(0, ude.start-10):ude.start+10]}")
                
                # Try to find the actual end of the XML by looking for closing tags
                xml_end_patterns = [b'</LSV>', b'</CSV>', b'</ESV>']
                for pattern in xml_end_patterns:
                    pos = decrypted_clean.find(pattern)
                    if pos != -1:
                        end_pos = pos + len(pattern)
                        truncated = decrypted_clean[:end_pos]
                        if debug:
                            print(f"[DEBUG] Found XML end pattern {pattern} at position {pos}")
                            print(f"[DEBUG] Truncated length: {len(truncated)}")
                        try:
                            return truncated.decode('utf-8')
                        except UnicodeDecodeError:
                            continue
                
                # If no valid XML end found, try errors='ignore'
                result = decrypted_clean.decode('utf-8', errors='ignore')
                if debug:
                    print(f"[DEBUG] Using errors='ignore', result length: {len(result)}")
                return result
                
        except Exception as e:
            print(f"Decryption error: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            return None

    def make_request(self, payload_xml: str, debug: bool = False) -> Optional[str]:
        """Make HTTP request to the /smart endpoint"""
        # Encrypt the XML payload
        encrypted_payload = self.encrypt_payload(payload_xml)
        
        # Create the full XML request body
        request_body = f'<?xml version="1.0" encoding="UTF-8"?><ESV>{encrypted_payload}</ESV>'
        
        if debug:
            print("[DEBUG] Request Body:")
            print(request_body)

        headers = {
            'Host': f'{self.device_ip}:80',
            'Content-Type': 'text/plain;chrset=UTF-8',
            'Connection': 'keep-alive',
            'Proxy-Connection': 'keep-alive',
            'Accept': '*/*',
            'User-Agent': 'KirigamineRemote/5.1.0 (jp.co.MitsubishiElectric.KirigamineRemote; build:3; iOS 17.5.1) Alamofire/5.9.1',
            'Accept-Language': 'zh-Hant-JP;q=1.0, ja-JP;q=0.9',
        }
        
        url = f'http://{self.device_ip}/smart'
        
        try:
            response = self.session.post(url, data=request_body, headers=headers, timeout=10)
            
            if response.status_code == 200:
                if debug:
                    print("[DEBUG] Response Text:")
                    print(response.text)
                try:
                    root = ET.fromstring(response.text)
                    encrypted_response = root.text
                    if encrypted_response:
                        decrypted = self.decrypt_payload(encrypted_response, debug=debug)
                        return decrypted
                except ET.ParseError as e:
                    print(f"XML parsing error: {e}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None


    def send_status_request(self, debug: bool = False) -> Optional[str]:
        """Send a status request to get current device state"""
        payload_xml = '<CSV><CONNECT>ON</CONNECT></CSV>'
        return self.make_request(payload_xml, debug=debug)

    def send_echonet_enable(self, debug: bool = False) -> Optional[str]:
        """Send ECHONET enable command"""
        payload_xml = '<CSV><CONNECT>ON</CONNECT><ECHONET>ON</ECHONET></CSV>'
        return self.make_request(payload_xml, debug=debug)

    def send_hex_command(self, hex_command: str, debug: bool = False) -> Optional[str]:
        """Send a hex command to the device"""
        payload_xml = f'<CSV><CONNECT>ON</CONNECT><CODE><VALUE>{hex_command}</VALUE></CODE></CSV>'
        return self.make_request(payload_xml, debug=debug)

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
