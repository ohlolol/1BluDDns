import re
import requests
import logging
import dns_records
import session

base_url = "https://ksb.1blu.de"



default_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0",
}

class Api:
    """Api to the 1Blu server"""
    def __init__(self, username : str, password : str, otp_key : str, domain_number : str, contract:str) -> None:
        self._dns_base_url : str = f"{base_url}/{contract}/domain/{domain_number}/dns"
        self._session : session.Session = session.Session(username, password, otp_key)
        self._records = None



    def fetch_records(self) -> bool:
        """Fetches the current dns-records from the 1blu interface. They are recieved as json inside the html-document"""
        response = self._session.get(url=self._dns_base_url)


        if(response.status_code != 200):
            logging.error(f"connection error: [GET]'{base_url}' responded with status-code {response.status_code}")
            return False

        re_json_data = re.search(r"\"dataSource\":{\"data\":(\[[^\"]*?(?:\"[^\"]*?\"[^\"]*?)*\])", response.text)

        if(re_json_data is None):
            logging.error("could not find dns records")
            return False

        self._records =  dns_records.from_json(re_json_data.group(1))
        #TODO: can from_json fail?
        logging.info(f"found dns records: {self._records}")
        return True


    def push_records(self):
        """Pushes dns-records to 1blu. This is done via a POST request with the records encoded as form-url."""
        if(self._records is None):
            logging.error("cant push records, because records are None")
            return

        content = dns_records.to_form_url_encoded(self._records)
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0",
            "Content-Type" : "application/x-www-form-urlencoded",
            "Content-Length" : str(len(content)),
        }
        url = f"{self._dns_base_url}/setdnsrecords/"
        logging.info(f"posting to: {url}")
        response = self._session.post(url=url,headers=headers,data=content)
        logging.info(f'pushed records: {response.text}')
        #TODO: test result


    def update_address(self, subdomain :str, rrtype: str, new_target:str):
        """Updates a url on 1Blu by fetching the current records, updating them and pushing them back again."""
        self.fetch_records()
        if(self._records is None):
            logging.error("fetching dns-records failed!")
            return

        hostname = subdomain if subdomain != "" else "@"

        logging.info(f"modifiing record: {hostname} [{rrtype}] to address: '{new_target}'")

        for record in self._records:
            if(record["hostname"] is not hostname):
                continue
            if(record["type"] is not rrtype):
                continue

            record["target"] = new_target
            record["modified"] = "1"
            logging.info(f"modified record with id {record['id']}")

        self.push_records()

