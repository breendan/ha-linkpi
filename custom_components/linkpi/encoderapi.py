### LinkPI HDMI Encoder Code
### API Docs located here https://www.yuque.com/linkpi/encoder/pxggvc7oq2prg45b

import hashlib
import logging
import os
import json
import aiohttp
import asyncio
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT = 10  # seconds

class LinkPiEncoder:
    def __init__(self, host, username, password):
        self._host = host
        self._username = username
        self._password = password
        self._session = aiohttp.ClientSession()
        self._login_data = None
        self._digest_challenge = None

    async def login(self):
        url = f"http://{self._host}/link/user/lph_login"
        uri = "/link/user/lph_login"
        hashed_password = hashlib.md5(self._password.encode("utf-8")).hexdigest()
        payload = {"username": self._username, "passwd": hashed_password}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            async with self._session.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status == 401:
                    challenge_header = resp.headers.get("WWW-Authenticate")
                    if not challenge_header:
                        raise Exception("No WWW-Authenticate header in 401 login response")
                    self._digest_challenge = self.parse_www_authenticate(challenge_header)
                    auth_header = self.build_digest_header(
                        self._username, self._password, "POST", uri, self._digest_challenge
                    )
                    headers["Authorization"] = auth_header
                    async with self._session.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT) as resp2:
                        result = await resp2.json()
                        if result.get("status") == "success" and "L-HASH" in result.get("data", {}):
                            self._login_data = result["data"]
                            _LOGGER.info("Login successful with digest auth")
                            _LOGGER.debug(
                                "Login successful. Session hashes: L-HASH=%s, P-HASH=%s, H-HASH=%s",
                                self._login_data.get("L-HASH"),
                                self._login_data.get("P-HASH"),
                                self._login_data.get("H-HASH"),
                            )
                            return True
                        raise Exception(f"Login failed: {result}")
                elif resp.status == 200:
                    result = await resp.json()
                    if result.get("status") == "success" and "L-HASH" in result.get("data", {}):
                        self._login_data = result["data"]
                        _LOGGER.info("Login successful without digest auth")
                        _LOGGER.debug(
                            "Login successful. Session hashes: L-HASH=%s, P-HASH=%s, H-HASH=%s",
                            self._login_data.get("L-HASH"),
                            self._login_data.get("P-HASH"),
                            self._login_data.get("H-HASH"),
                        )
                        return True
                    raise Exception(f"Login failed: {result}")
                else:
                    text = await resp.text()
                    raise Exception(f"Unexpected login response {resp.status}: {text}")

        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            raise

    def get_auth_headers(self):
        if not self._login_data:
            raise Exception("Not logged in")
        return {
            "L-HASH": self._login_data["L-HASH"],
            "P-HASH": self._login_data["P-HASH"],
            "H-HASH": self._login_data["H-HASH"],
            "Cookie": self._login_data["Cookie"],
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

    async def _digest_post(self, endpoint, retry=True):
        url = f"http://{self._host}{endpoint}"

        # Ensure we have a digest challenge to build auth header
        if not self._digest_challenge:
            try:
                async with self._session.post(url, json={}, timeout=_REQUEST_TIMEOUT) as resp:
                    if resp.status == 401:
                        challenge_header = resp.headers.get("WWW-Authenticate")
                        if challenge_header:
                            self._digest_challenge = self.parse_www_authenticate(challenge_header)
                            _LOGGER.debug("Obtained digest challenge for endpoint %s", endpoint)
                        else:
                            raise UpdateFailed("No digest challenge received from device")
                    else:
                        result = await resp.json()
                        if result.get("status") == "success":
                            return result["data"]
                        else:
                            raise UpdateFailed(f"{endpoint} error: {result.get('msg')}")
            except asyncio.TimeoutError as e:
                # Explicit timeout message
                msg = (
                    f"Timeout after {_REQUEST_TIMEOUT}s obtaining digest challenge for {endpoint}; "
                    "will retry automatically on next poll"
                )
                _LOGGER.error(msg)
                raise UpdateFailed(msg) from e
            except Exception as e:
                _LOGGER.error(
                    "Error getting digest challenge for %s: %s (%s)",
                    endpoint,
                    e,
                    e.__class__.__name__,
                )
                raise UpdateFailed(
                    f"Error getting digest challenge for {endpoint}: {e.__class__.__name__}: {e}"
                ) from e

        # Build Digest Authorization header for the request
        auth_header = self.build_digest_header(
            self._username, self._password, "POST", endpoint, self._digest_challenge
        )
        # Add session authentication hashes to headers
        headers = self.get_auth_headers()
        headers["Authorization"] = auth_header

        _LOGGER.debug(
            "Using session hashes for request to %s: L-HASH=%s, P-HASH=%s, H-HASH=%s",
            endpoint,
            headers.get("L-HASH"),
            headers.get("P-HASH"),
            headers.get("H-HASH"),
        )

        try:
            async with self._session.post(url, headers=headers, json={}, timeout=_REQUEST_TIMEOUT) as resp:
                text = await resp.text()

                # Handle unauthorized, possibly due to expired session keys or nonce
                if resp.status == 401:
                    if not retry:
                        raise UpdateFailed(f"{endpoint} unauthorized even after retry")
                    _LOGGER.info("Session expired or unauthorized (401) for %s, re-logging in", endpoint)
                    self._login_data = None
                    self._digest_challenge = None
                    await self.login()
                    return await self._digest_post(endpoint, retry=False)

                if resp.status != 200:
                    raise UpdateFailed(f"{endpoint} failed: HTTP {resp.status}, body: {text[:200]}")

                # Parse JSON response safely
                try:
                    result = json.loads(text)
                except json.JSONDecodeError as err:
                    raise UpdateFailed(f"Failed to decode JSON from {endpoint}: {err}") from err

                # Check for API-level error
                if result.get("status") != "success":
                    msg = (result.get("msg") or "")
                    if "please login first" in msg.lower():
                        if not retry:
                            raise UpdateFailed(f"{endpoint} error: {msg} even after retry")
                        _LOGGER.info("API requested login for %s; re-logging in", endpoint)
                        self._login_data = None
                        self._digest_challenge = None
                        await self.login()
                        return await self._digest_post(endpoint, retry=False)
                    raise UpdateFailed(f"{endpoint} error: {msg}")

                return result["data"]

        except asyncio.TimeoutError as err:
            msg = (
                f"Timeout after {_REQUEST_TIMEOUT}s calling {endpoint}; "
                "will retry automatically on next poll"
            )
            _LOGGER.error(msg)
            raise UpdateFailed(msg) from err

        except UpdateFailed:
            # Already formatted; just propagate
            raise

        except Exception as err:
            _LOGGER.error(
                "Request error for %s: %s (%s)",
                endpoint,
                err,
                err.__class__.__name__,
            )
            raise UpdateFailed(
                f"Error communicating with LinkPi: {err.__class__.__name__}: {err}"
            ) from err

    async def get_sys_state(self):
        return await self._digest_post("/link/system/get_sys_state")

    async def get_net_state(self):
        return await self._digest_post("/link/system/get_net_state")

    async def get_vi_state(self):
        return await self._digest_post("/link/system/get_vi_state")

    async def logout(self):
        if not self._login_data:
            return
        url = f"http://{self._host}/link/user/lph_logout"
        headers = self.get_auth_headers()
        if self._digest_challenge:
            headers["Authorization"] = self.build_digest_header(
                self._username, self._password, "POST", "/link/user/lph_logout", self._digest_challenge
            )
        try:
            async with self._session.post(url, headers=headers, json={}, timeout=_REQUEST_TIMEOUT):
                pass
        except Exception as err:
            _LOGGER.warning("Logout error: %s", err)

    async def close(self):
        await self.logout()
        await self._session.close()

    @staticmethod
    def parse_www_authenticate(header):
        parts = header.replace("Digest ", "").split(",")
        return {k: v.strip('"') for part in parts if "=" in part for k, v in [part.strip().split("=", 1)]}

    @staticmethod
    def build_digest_header(username, password, method, uri, challenge):
        realm = challenge.get('realm', '')
        nonce = challenge.get('nonce', '')
        qop = challenge.get('qop', 'auth')
        opaque = challenge.get('opaque', '')
        nc = "00000001"
        cnonce = os.urandom(8).hex()
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode("utf-8")).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode("utf-8")).hexdigest()
        response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode("utf-8")).hexdigest()
        return (
            f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
            f'algorithm="MD5", response="{response}", qop={qop}, nc={nc}, cnonce="{cnonce}", opaque="{opaque}"'
        )
