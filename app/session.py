import re
from typing import Optional
import requests
import logging
import pyotp

base_url = "https://ksb.1blu.de"
default_headers = {
    "User-Agent": "Mozilla/5.0",
}

class Session:
    """Represents a session with the server and handles the login"""
    #TODO: Error, when a opt is needed but not given
    def __init__(self, username : str, password : str, otp_key : str) -> None:
        self._username = username
        self._password = password
        self._session : requests.Session = requests.Session() 
        self._totp : Optional[pyotp.TOTP] = pyotp.TOTP(otp_key) if otp_key != "" else None
        self._create()
        self._log_in()
        

    def _create(self) -> None:
        """Creates new session"""
        response = self._session.get(url=base_url, headers=default_headers)
        if(response.status_code != 200):
            logging.error(f"Failed to create new session: '{base_url}' responded with status-code {response.status_code}.")
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

        self._password_login()
        if(self._totp is not None):
            self._2fa_login()
        
        self._validate_successful_login()

        
        

    def _password_login(self):
        """Does the password login for the current Session."""
        csrf_token = self._get_csrf_token(base_url)
        if(csrf_token == ""):
            logging.error("Failed to log in: no csrf-token")
            return

        content = f"_username={self._username}&_password={self._password}&_csrf_token={csrf_token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }

        response = self._session.post(url=base_url,headers=headers,data=content)
        
        if(not self._validate_password_login(response)):
            return

        logging.info("Password-login successful.")

    def _validate_password_login(self, response: requests.Response) -> bool:
        """Validates, if the Password login was sucessful by checking the title of the response. If not it logs an error message"""
        if(response.status_code != 200):
            logging.error(f"Failed to log in : '{base_url}' responded with status-code {response.status_code}")
            return False

        re_title = re.search(r"<title>(.*?)</title>", response.text)
        
        if(re_title is None):
            logging.error("Failed to log in: Unknown error (returned to unknown page with no title)")
            return False
        
        title = re_title.group(1)

        if(title == "Kundenlogin"):
            re_errors = re.findall(r"<div[^>]*?class=\"alert alert-danger\"[^>]*?>([\s\S]*?)<\/div>", response.text)
            for error in re_errors:
                
                
                if("Ungültiges CSRF-Token" in error):
                    logging.error('Failed to log in: Inavlid CSRF-Token')
                    return False

                if("Falsche Zugangsdaten" in error):
                    logging.error('Failed to log in: Wrong Credentials')
                    return False
                
                logging.debug(f"Found error message on page: '{error}'")
            
            logging.error('Failed to log in: Unknown error (returned to login page)')
            return False

        if(title != "2-Faktor-Authentisierung"):
            logging.error(f"Failed to log in: Unknown error (returned to page: '{title}')")
            return False

        return True

    def _2fa_login(self):
        """Does the 2fa for the current Session"""
        logging.info("2fa...")
        csrf_token = self._get_csrf_token(f"{base_url}/2fa/")

        if(csrf_token == ""):
            logging.error("Failed to 2fa: No csrf-token")
            return

        if(self._totp is None):
            logging.error("Failed to 2fa: No OTP-Key")
            return

        auth_code = self._totp.now()
        content = f"_auth_code={auth_code}&_csrf_token={csrf_token}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }
        
        response = self._session.post(url=f"{base_url}/2fa_check/",headers=headers,data=content)

        if(not self._validate_2fa_login(response)):
            return

        logging.info("2fa successful.")

    def _validate_2fa_login(self, response : requests.Response) -> bool:
        """Validates, if the 2fa was successful by checking the title of the response. If not it logs an error message"""
        if(response.status_code != 200):
            logging.error(f"Failed to 2fa: '{base_url}' responded with status-code {response.status_code}")
            return False
        
        re_title = re.search(r"<title>(.*?)</title>", response.text)
        
        if(re_title is None):
            logging.error("Failed to log in: Unknown error (returned to unknown page with no title)")
            return False
        
        title = re_title.group(1)

        if(title == "2-Faktor-Authentisierung"):
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


        if(title != "Start"):
            logging.error("Failed to log in: Unknown error (returned to page: '{title}')")
            return False

        return True
    
    def _validate_successful_login(self) -> bool:
        """Validates, if the login process was successful by testing if the start page can be loaded"""
        response = self._session.get(url=f"{base_url}/start/",headers=default_headers)
        re_title = re.search(r"<title>(.*?)</title>", response.text)
        
        if(re_title is None):
            logging.error("Unsuccessful login: Returned to unknown page with no title")
            return False

        title = re_title.group(1)
        
        if(title != "Start"):
            logging.error(f"Unsuccessful login: Returned to page: '{title}'")
            return False

        return True


    def get(self, url:str, headers=default_headers,data=None):
        return self._session.get(url, headers=headers,data=data)

    def post(self, url:str, headers=default_headers,data=None):
        return self._session.post(url, headers=headers,data=data)
