import re
from tracemalloc import start
from typing import Optional
import requests
import logging
import pyotp

URL_BASE = "https://ksb.1blu.de"
URL_LOGIN = f"{URL_BASE}/"
URL_2FA = f"{URL_BASE}/2fa/"
URL_START = f"{URL_BASE}/start/"
URL_2FA_CHECK = f"{URL_BASE}/2fa_check/"

default_headers = {
    "User-Agent": "Mozilla/5.0",
}

class Session:
    """Represents a session with the server and handles the login"""
    def __init__(self, username : str, password : str, otp_key : str) -> None:
        self._username = username
        self._password = password
        self._session : requests.Session = requests.Session() 
        self._totp : Optional[pyotp.TOTP] = pyotp.TOTP(otp_key) if otp_key != "" else None
        self._create()
        self._log_in()
        

    def _create(self) -> None:
        """Creates new session"""
        #TODO: disable cookie banner
        response = self._session.get(url=URL_LOGIN, headers=default_headers)
        if(response.status_code != 200):
            logging.error(f"Failed to create new session: '{URL_LOGIN}' responded with status-code {response.status_code}.")
            return

        if('PHPSESSID' not in self._session.cookies):
            logging.error("Failed to create new session: No session id found.")
            return

        logging.info(f"Created new session with id: '{self._session.cookies['PHPSESSID']}' ")


   
    def _get_csrf_token(self, url:str) -> str:
        """Returns a csrf-token, which is located in a hidden input field inside a form"""
        logging.info("Retrieving csrf-token...")
        response = self._session.get(url=url,headers=default_headers)

        if(response.status_code != 200):
            logging.error(f"Failed to retrieve csrf-token: '{url}' responded with status-code {response.status_code}.")
            return ""

        re_token = re.search(r"<input[^>]*?name=\"_csrf_token\"[^>]*?value=\"(.*?)\"[^>]*?\>", response.text)

        if(re_token is None):
            logging.error(f"Failed to find csrf-token for url: '{url}'")
            return ""

        csrf_token = re_token.group(1)
        logging.info(f"Found csrf-token for '{url}': '{csrf_token}'")
        return csrf_token


    def _log_in(self) -> None:
        """Does the login of the current session."""
        logging.info("Logging into account...")


        csrf_token = self._get_csrf_token(URL_LOGIN)
        if(csrf_token == ""):
            logging.error("Failed to log in: no csrf-token")
            return

        content = f"_username={self._username}&_password={self._password}&_csrf_token={csrf_token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }

        response = self._session.post(url=URL_LOGIN,headers=headers,data=content)
        
        if(not self._validate_password_login(response)):
            logging.error("Failed to log in: Validation failed.")
            return

        logging.info("Password-login successful.")

        opt_needed = response.url == URL_2FA
        
        if(opt_needed):
            self._2fa_login()
        
        if(not self.is_session_valid()):
            logging.error("Failed to log in: Verification failed.")
            return

        

    def _validate_password_login(self, response: requests.Response) -> bool:
        """Validates, if the Password login was sucessful by checking the title of the response. If not it logs an error message"""
        if(response.status_code != 200):
            logging.error(f"Failed to log in : '{URL_LOGIN}' responded with status-code {response.status_code}")
            return False


        if(response.url == URL_LOGIN):
            re_errors = re.findall(r"<div[^>]*?class=\"alert alert-danger\"[^>]*?>([\s\S]*?)<\/div>", response.text)
            for error in re_errors:
                
                
                if("Ungültiges CSRF-Token" in error):
                    logging.error('Failed to log in: Inavlid CSRF-Token.')
                    return False

                if("Falsche Zugangsdaten" in error):
                    logging.error('Failed to log in: Wrong Credentials.')
                    return False
                
                logging.debug(f"Found error message on page: '{error}'.")
            
            logging.error('Failed to log in: Unknown error (returned to login page).')
            return False

        if(response.url not in [URL_2FA, URL_START]):
            logging.error(f"Failed to log in: Redirected to unknown url: '{response.url}'")
            return False

        return True

    def _2fa_login(self):
        """Does the 2fa for the current Session"""
        logging.info("2fa...")

        if(self._totp is None):
            logging.error("Failed to 2fa: No OTP-Key")
            return

        csrf_token = self._get_csrf_token(URL_2FA)

        if(csrf_token == ""):
            logging.error("Failed to 2fa: No csrf-token")
            return



        auth_code = self._totp.now()
        content = f"_auth_code={auth_code}&_csrf_token={csrf_token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }
        
        response = self._session.post(url=URL_2FA_CHECK,headers=headers,data=content)

        if(not self._validate_2fa_login(response)):
            return

        logging.info("2fa successful.")

    def _validate_2fa_login(self, response : requests.Response) -> bool:
        """Validates, if the 2fa was successful by checking the title of the response. If not it logs an error message"""
        if(response.status_code != 200):
            logging.error(f"Failed to 2fa: '{URL_2FA}' responded with status-code {response.status_code}")
            return False
        
        if(response.url == URL_2FA):
            re_errors = re.findall(r"<div[^>]*?class=\"alert alert-danger\"[^>]*?>([\s\S]*?)<\/div>", response.text)
            for error in re_errors:
                
                if("Ungültiges CSRF-Token" in error):
                    logging.error('Failed to 2fa: Inavlid CSRF-Token')
                    return False

                if("Der Bestätigungs-Code ist nicht korrekt" in error):
                    logging.error('Failed to 2fa: Inavlid OTP')
                    return False

                logging.debug(f"Found error message on page: '{error}'")
            
            logging.error('Failed to 2fa: Unknown error (returned to 2fa page)')
            return False


        if(response.url != URL_START):
            logging.error(f"Failed to log in: Unknown error (redirected to page: '{response.url}')")
            return False

        return True
    
    def is_session_valid(self) -> bool:
        """Validates, if a session is still valid and logged in"""
        response = self._session.get(url=URL_START,headers=default_headers)
        return response.url == URL_START

    def get(self, url:str, headers=default_headers,data=None):
        return self._session.get(url, headers=headers,data=data)


    def post(self, url:str, headers=default_headers,data=None):
        return self._session.post(url, headers=headers,data=data)
