#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner API Communication Layer

This module handles all HTTP communication, encryption, and decryption
for Mitsubishi MAC-577IF-2E devices.
"""

import base64
import re
import requests
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any

# Constants from the working implementation
KEY_SIZE = 16
STATIC_KEY = "unregistered"


class MitsubishiAPI:
    """Handles all API communication with Mitsubishi AC devices"""
    
    def __init__(self, device_ip: str, encryption_key: str = STATIC_KEY, admin_username: str = "admin", admin_password: str = "me1debug@0567"):
        self.device_ip = device_ip
        self.encryption_key = encryption_key
        self.admin_username = admin_username
        self.admin_password = admin_password
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

    def get_unit_info(self, admin_password: str = None, debug: bool = False) -> Optional[Dict[str, Any]]:
        """Get unit information from the /unitinfo endpoint using admin credentials"""
        try:
            url = f'http://{self.device_ip}/unitinfo'
            # Use provided password or fall back to instance default
            password = admin_password or self.admin_password
            auth = HTTPBasicAuth(self.admin_username, password)
            
            if debug:
                print(f"[DEBUG] Fetching unit info from {url}")
            
            response = self.session.get(url, auth=auth, timeout=10)
            
            if response.status_code == 200:
                if debug:
                    print(f"[DEBUG] Unit info HTML response received ({len(response.text)} chars)")
                
                # Parse the HTML response to extract unit information
                return self._parse_unit_info_html(response.text, debug=debug)
            else:
                if debug:
                    print(f"[DEBUG] Unit info request failed with status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            if debug:
                print(f"[DEBUG] Unit info request error: {e}")
            return None
    
    def _parse_unit_info_html(self, html_content: str, debug: bool = False) -> Dict[str, Any]:
        """Parse unit info HTML response to extract structured data"""
        unit_info = {
            'adaptor_info': {},
            'unit_info': {}
        }
        
        try:
            # Extract data using regex patterns to parse the HTML structure
            # Pattern to match <dt>Label</dt><dd>Value</dd> pairs
            pattern = r'<dt>([^<]+)</dt>\s*<dd>([^<]+)</dd>'
            matches = re.findall(pattern, html_content)
            
            if debug:
                print(f"[DEBUG] Found {len(matches)} key-value pairs in HTML")
            
            # Determine which section we're in based on the order and known fields
            adaptor_fields = {
                'Adaptor name', 'Application version', 'Release version', 'Flash version',
                'Boot version', 'Common platform version', 'Test release version',
                'MAC address', 'ID', 'Manufacturing date', 'Current time', 'Channel',
                'RSSI', 'IT communication status', 'Server operation', 
                'Server communication status', 'Server communication status(HEMS)',
                'SOI communication status', 'Thermal image timestamp'
            }
            
            unit_fields = {
                'Unit type', 'IT protocol version', 'Error'
            }
            
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                
                if key in adaptor_fields:
                    # Convert specific fields to appropriate types
                    if key == 'RSSI':
                        # Extract numeric value from "-25dBm" format
                        rssi_match = re.search(r'(-?\d+)', value)
                        if rssi_match:
                            unit_info['adaptor_info']['rssi_dbm'] = int(rssi_match.group(1))
                        unit_info['adaptor_info']['rssi_raw'] = value
                    elif key == 'Channel':
                        try:
                            unit_info['adaptor_info']['wifi_channel'] = int(value)
                        except ValueError:
                            unit_info['adaptor_info']['wifi_channel_raw'] = value
                    elif key == 'ID':
                        try:
                            unit_info['adaptor_info']['device_id'] = int(value)
                        except ValueError:
                            unit_info['adaptor_info']['device_id_raw'] = value
                    elif key == 'MAC address':
                        unit_info['adaptor_info']['mac_address'] = value
                    elif key == 'Manufacturing date':
                        unit_info['adaptor_info']['manufacturing_date'] = value
                    elif key == 'Current time':
                        unit_info['adaptor_info']['current_time'] = value
                    elif key == 'Adaptor name':
                        unit_info['adaptor_info']['model'] = value
                    elif key == 'Application version':
                        unit_info['adaptor_info']['app_version'] = value
                    elif key == 'Release version':
                        unit_info['adaptor_info']['release_version'] = value
                    elif key == 'Flash version':
                        unit_info['adaptor_info']['flash_version'] = value
                    elif key == 'Boot version':
                        unit_info['adaptor_info']['boot_version'] = value
                    elif key == 'Common platform version':
                        unit_info['adaptor_info']['platform_version'] = value
                    elif key == 'Test release version':
                        unit_info['adaptor_info']['test_version'] = value
                    elif key == 'IT communication status':
                        unit_info['adaptor_info']['it_comm_status'] = value
                    elif key == 'Server operation':
                        unit_info['adaptor_info']['server_operation'] = value == 'ON'
                    elif key == 'Server communication status':
                        unit_info['adaptor_info']['server_comm_status'] = value
                    elif key == 'Server communication status(HEMS)':
                        unit_info['adaptor_info']['hems_comm_status'] = value
                    elif key == 'SOI communication status':
                        unit_info['adaptor_info']['soi_comm_status'] = value
                    elif key == 'Thermal image timestamp':
                        unit_info['adaptor_info']['thermal_timestamp'] = value if value != '--' else None
                    else:
                        # Fallback: store with normalized key
                        normalized_key = key.lower().replace(' ', '_').replace('(', '').replace(')', '')
                        unit_info['adaptor_info'][normalized_key] = value
                        
                elif key in unit_fields:
                    if key == 'Unit type':
                        unit_info['unit_info']['type'] = value
                    elif key == 'IT protocol version':
                        unit_info['unit_info']['it_protocol_version'] = value
                    elif key == 'Error':
                        unit_info['unit_info']['error_code'] = value
                    else:
                        # Fallback: store with normalized key
                        normalized_key = key.lower().replace(' ', '_')
                        unit_info['unit_info'][normalized_key] = value
            
            if debug:
                print(f"[DEBUG] Parsed unit info: {len(unit_info['adaptor_info'])} adaptor fields, {len(unit_info['unit_info'])} unit fields")
            
            return unit_info
            
        except Exception as e:
            if debug:
                print(f"[DEBUG] Error parsing unit info HTML: {e}")
            return {'adaptor_info': {}, 'unit_info': {}, 'parse_error': str(e)}

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
