from typing import Dict, List, Optional
import json
import logging



def from_json(input : str) -> Optional[List[Dict]]:
    dns_records = json.loads(input)
    if(not is_valid_records_syntax(dns_records)):
        logging.error(f"records have invalid syntax: {input}")
        return None
    return dns_records

def is_valid_records_syntax(records):
    if(type(records) is not list):
        logging.error("records are not a list")
        return False

    for record in records:
        
        if type(record) is not dict:
            logging.error("a record is not a dictionary")
            return False

        if("id" not in record):
            logging.error("record needs id but has none")
            return False
        
    return True



def to_form_url_encoded(records : List[Dict]) -> str:
    output : str = ""
    for record in records:
        for key in record.keys():
            if(output != ""): 
                output += "&"
            output += f"records[{record['id']}][{key}]={record[key]}"
    return output

