from multiprocessing.connection import wait
import re
from time import sleep
import requests
import logging
import pyotp

base_url = "https://ksb.1blu.de"
default_headers = {
    "User-Agent": "Mozilla/5.0",
}

class Session:

    def __init__(self, username : str, password : str, otp_key : str) -> None:
        self._session = requests.Session()
        print(f"'{otp_key}'")
        self._totp = pyotp.TOTP(otp_key)
        self._create()
        self._log_in(username, password)
        

    def _create(self) -> None:
        response = self._session.get(url=base_url, headers=default_headers)
        logging.info(f"created new session with id: '{self._session.cookies['PHPSESSID']}' ")


   
    def _get_csrf_token(self, url:str) -> str:
        response = self._session.get(url=url,headers=default_headers)

        if(response.status_code != 200):
            logging.error(f"connection error: [GET]'{url}' responded with status-code {response.status_code}")
            return ""

        re_token = re.search(r"<input[^>]*?name=\"_csrf_token\"[^>]*?value=\"(.*?)\"[^>]*?\>", response.text)

        if(re_token is None):
            logging.error(f"could not find csrf-token for '{url}'")
            return ""

        csrf_token = re_token.group(1)
        logging.info(f"found csrf-token for '{url}': '{csrf_token}'")
        return csrf_token


    def _log_in(self, username : str, password:str) -> None:
        logging.info("logging in...")
        #username and password
        csrf_token = self._get_csrf_token(base_url)
        if(csrf_token == ""):
            logging.error("csrf-token empty")
            return

        content = f"_username={username}&_password={password}&_csrf_token={csrf_token}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }

        response = self._session.post(url=base_url,headers=headers,data=content)
        
        if(response.status_code != 200):
            logging.error(f"connection error: [POST]'{base_url}' responded with status-code {response.status_code}")
            return
        
        logging.info("log-in complete.")
        
        #otp
        logging.info("doing 2fa...")
        csrf_token = self._get_csrf_token(f"{base_url}/2fa/")

        if(csrf_token == ""):
            logging.error("csrf-token empty")
            return


        auth_code = self._totp.now()
        content = f"_auth_code={auth_code}&_csrf_token={csrf_token}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }
        
        response = self._session.post(url=f"{base_url}/2fa_check/",headers=headers,data=content)

        if(response.status_code != 200):
            logging.error(f"connection error: [POST]'{base_url}' responded with status-code {response.status_code}")
            return
        
        logging.info("2fa complete.")


    def get(self, url:str, headers=default_headers,data=None):
        return self._session.get(url, headers=headers,data=data)

    def post(self, url:str, headers=default_headers,data=None):
        return self._session.post(url, headers=headers,data=data)
