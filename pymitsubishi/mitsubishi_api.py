#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner API Communication Layer

This module handles all HTTP communication, encryption, and decryption
for Mitsubishi MAC-577IF-2E devices.
"""

import base64
import logging
import re
from typing import Any
import xml.etree.ElementTree as ET

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

# Constants from the working implementation
KEY_SIZE = 16
STATIC_KEY = b"unregistered\0\0\0\0"  # Use bytes directly with proper padding

logger = logging.getLogger(__name__)


class MitsubishiAPI:
    """Handles all API communication with Mitsubishi AC devices"""

    def __init__(
        self,
        device_host_port: str,
        encryption_key: bytes | str = STATIC_KEY,
        admin_username: str = "admin",
        admin_password: str = "me1debug@0567",
    ):
        self.device_host_port = device_host_port
        # Handle both bytes and string encryption keys
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode("utf-8")
        # Ensure key is exactly KEY_SIZE bytes
        if len(encryption_key) < KEY_SIZE:
            encryption_key += (KEY_SIZE - len(encryption_key)) * b"\0"  # pad with NULL-bytes
        self.encryption_key = encryption_key[:KEY_SIZE]  # trim if too long
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.session = requests.Session()

        # Add retry logic with backoff for better reliability
        retries = Retry(total=4, backoff_factor=1)
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def get_crypto_key(self) -> bytes:
        """Get the crypto key - now just returns the properly sized key"""
        return self.encryption_key

    def encrypt_payload(self, payload: str, iv: bytes | None = None) -> str:
        """Encrypt payload using AES-CBC with proper padding"""
        if iv is None:  # Allow passing in IV for testing purposes
            iv = get_random_bytes(KEY_SIZE)

        # Encrypt using AES CBC with ISO 7816-4 padding
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)

        payload_bytes = payload.encode("utf-8")
        padded_payload = pad(payload_bytes, KEY_SIZE, "iso7816")

        encrypted = cipher.encrypt(padded_payload)

        # Combine IV and encrypted data, then base64 encode
        return base64.b64encode(iv + encrypted).decode("utf-8")

    def decrypt_payload(self, payload_b64: str) -> str:
        logger.debug(f"Base64 payload length: {len(payload_b64)}")

        # Convert base64 directly to bytes
        encrypted = base64.b64decode(payload_b64)  # may raise

        # Extract IV and encrypted data
        iv = encrypted[:KEY_SIZE]
        encrypted_data = encrypted[KEY_SIZE:]

        logger.debug(f"IV: {iv.hex()}")
        logger.debug(f"Encrypted data length: {len(encrypted_data)}")

        # Decrypt using AES CBC
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)  # may raise, e.g. when invalid length

        logger.debug(f"Decrypted raw length: {len(decrypted)}")

        # Try to remove ISO 7816-4 padding first
        try:
            decrypted_clean = unpad(decrypted, KEY_SIZE, "iso7816")
        except ValueError:
            # Fall back to removing zero padding if ISO padding fails
            logger.debug("ISO 7816-4 unpadding failed, using zero padding removal")
            decrypted_clean = decrypted.rstrip(b"\x00")

        logger.debug(f"After padding removal length: {len(decrypted_clean)}")

        # Try to decode as UTF-8
        try:
            result: str = decrypted_clean.decode("utf-8")
            logger.debug(f"Decrypted XML response: {result}")
            return result
        except UnicodeDecodeError as ude:
            logger.debug(f"UTF-8 decode error at position {ude.start}: {ude.reason}")

            # Try to find the actual end of the XML by looking for closing tags
            xml_end_patterns = [b"</LSV>", b"</CSV>", b"</ESV>"]
            for pattern in xml_end_patterns:
                pos = decrypted_clean.find(pattern)
                if pos != -1:
                    end_pos = pos + len(pattern)
                    truncated = decrypted_clean[:end_pos]
                    logger.debug(f"Found XML end pattern {pattern.decode('utf-8')} at position {pos}")
                    try:
                        truncated_result: str = truncated.decode("utf-8")
                        return truncated_result
                    except UnicodeDecodeError:
                        continue

            # If no valid XML end found, try errors='ignore'
            fallback_result: str = decrypted_clean.decode("utf-8", errors="ignore")
            logger.debug(f"Using errors='ignore', result length: {len(fallback_result)}")
            return fallback_result

    def make_request(self, payload_xml: str) -> str:
        """Make HTTP request to the /smart endpoint"""
        # Encrypt the XML payload
        encrypted_payload = self.encrypt_payload(payload_xml)

        # Create the full XML request body
        request_body = f'<?xml version="1.0" encoding="UTF-8"?><ESV>{encrypted_payload}</ESV>'

        logger.debug("Request Body:")
        logger.debug(request_body)

        headers = {
            "Host": f"{self.device_host_port}",
            "Content-Type": "text/plain;chrset=UTF-8",
            "Connection": "keep-alive",
            "Proxy-Connection": "keep-alive",
            "Accept": "*/*",
            "User-Agent": "KirigamineRemote/5.1.0 (jp.co.MitsubishiElectric.KirigamineRemote; build:3; iOS 17.5.1) Alamofire/5.9.1",
            "Accept-Language": "zh-Hant-JP;q=1.0, ja-JP;q=0.9",
        }

        url = f"http://{self.device_host_port}/smart"

        response = self.session.post(url, data=request_body, headers=headers, timeout=2)  # may raise
        response.raise_for_status()  # may raise

        logger.debug("Response Text:")
        logger.debug(response.text)
        root = ET.fromstring(response.text)  # may raise
        encrypted_response = root.text
        if encrypted_response:
            decrypted = self.decrypt_payload(encrypted_response)
            return decrypted
        else:
            raise RuntimeError("Could not find any text in response")

    def send_reboot_request(self) -> str:
        return self.make_request("<CSV><RESET></RESET></CSV>")

    def send_status_request(self) -> str:
        """Send a status request to get current device state"""
        payload_xml = "<CSV><CONNECT>ON</CONNECT></CSV>"
        return self.make_request(payload_xml)

    def send_echonet_enable(self) -> str:
        """Send ECHONET enable command"""
        payload_xml = "<CSV><CONNECT>ON</CONNECT><ECHONET>ON</ECHONET></CSV>"
        return self.make_request(payload_xml)

    def send_command(self, command: bytes) -> str:
        return self.send_hex_command(command.hex())

    def send_hex_command(self, hex_command: str) -> str:
        payload_xml = f"<CSV><CONNECT>ON</CONNECT><CODE><VALUE>{hex_command}</VALUE></CODE></CSV>"
        return self.make_request(payload_xml)

    def get_unit_info(self) -> dict[str, Any]:
        """Get unit information from the /unitinfo endpoint using admin credentials"""
        url = f"http://{self.device_host_port}/unitinfo"
        auth = HTTPBasicAuth(self.admin_username, self.admin_password)

        logger.debug(f"Fetching unit info from {url}")

        response = self.session.get(url, auth=auth, timeout=2)  # may raise
        response.raise_for_status()

        logger.debug(f"Unit info HTML response received ({len(response.text)} chars)")

        # Parse the HTML response to extract unit information
        return self._parse_unit_info_html(response.text)

    @staticmethod
    def _parse_unit_info_html(html_content: str) -> dict[str, Any]:
        """Parse unit info HTML response to extract structured data"""
        # We should be using a full blown HTML parser, but let's brute force it with regexes
        # obligatory https://stackoverflow.com/a/1732454 reference

        unit_info: dict[str, dict[str, Any]] = {}
        section = ""
        pattern = r"(?:<(div) class=\"titleA\">([^<]*)</div>)|(?:<(dt)>([^<]+)</dt>\s*<dd>([^<]+)</dd>)"
        for match in re.findall(pattern, html_content):
            if match[0] == "div":
                section = match[1]
                unit_info.setdefault(section, {})
            elif match[2] == "dt":
                unit_info[section][match[3]] = match[4]
            else:
                raise ValueError("Unexpected regex match")

        # Type casting for specific fields
        try:
            unit_info["Adaptor Information"]["Channel"] = int(unit_info["Adaptor Information"]["Channel"])
        except KeyError:
            pass
        try:
            unit_info["Adaptor Information"]["RSSI"] = float(unit_info["Adaptor Information"]["RSSI"].rstrip("dBm"))
        except KeyError:
            pass

        return unit_info

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()
