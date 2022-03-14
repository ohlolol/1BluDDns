import re
import requests
import logging
import dns_records
import session

URL_BASE = "https://ksb.1blu.de"


default_headers = {
    "User-Agent": "Mozilla/5.0",
}

class Api:
    """Api to the 1Blu server"""
    def __init__(self, username : str, password : str, otp_key : str, domain_number : str, contract:str) -> None:
        self._URL_DNS_BASE : str = f"{URL_BASE}/{contract}/domain/{domain_number}/dns/"
        self._URL_SET_DNS : str = f"{self._URL_DNS_BASE}setdnsrecords/"
        self._session : session.Session = session.Session(username, password, otp_key)
        self._records = None



    def fetch_records(self) -> bool:
        """Fetches the current dns-records from the 1blu interface. They are recieved as json inside the html-document"""
        response = self._session.get(url=self._URL_DNS_BASE)

        if(response.status_code != 200):
            logging.error(f"Fetching records failed: '{self._URL_DNS_BASE}' responded with status-code {response.status_code}.")
            return False

        re_json_data = re.search(r"\"dataSource\":{\"data\":(\[[^\"]*?(?:\"[^\"]*?\"[^\"]*?)*\])", response.text)

        if(re_json_data is None):
            logging.error("Fetching records failed: Could not find dns records.")
            return False

        self._records =  dns_records.from_json(re_json_data.group(1))
        logging.debug(f"Fetched records: {self._records}.")
        return True


    def push_records(self) -> bool:
        """Pushes dns-records to 1blu. This is done via a POST request with the records encoded as form-url."""
        if(self._records is None):
            logging.error("Pushing records failed: No records found.")
            return False

        content = dns_records.to_form_url_encoded(self._records)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }
        response = self._session.post(url=self._URL_SET_DNS,headers=headers,data=content)
        logging.debug(f"Pushed records: {self._records}.")
        #TODO: validate result
        return True

    def update_address(self, subdomain :str, rrtype: str, new_target:str) -> bool:
        """Updates a url on 1Blu by fetching the current records, updating them and pushing them back again."""
        if(not self.fetch_records()):
            logging.error("Updating address failed: fetching records failed.")
            return False

        if(self._records is None):
            logging.error("Updating address failed: No dns records found.")
            return False

        hostname = subdomain if subdomain != "" else "@"

        for record in self._records:
            if(record["hostname"] != hostname):
                continue
            if(record["type"] != rrtype):
                continue

            record["target"] = new_target
            record["modified"] = "1"
            logging.info(f"Updating record: '{hostname}' [{rrtype}] to new address: '{new_target}'.")

        if(not self.push_records()):
            logging.error("Updating address failed: pushing records failed.")

        return True

