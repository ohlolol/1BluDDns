from typing import Dict, List, Optional
import json
import logging



def from_json(input : str) -> Optional[List[Dict]]:
    """Loads dns-records from json"""
    return json.loads(input)




def to_form_url_encoded(records : List[Dict]) -> str:
    """Converts dns-records to 'form url-encoded'. This format is used to update the dns-records on 1blu."""
    output : str = ""
    for record in records:
        for key in record.keys():
            if(output != ""): 
                output += "&"
            output += f"records[{record['id']}][{key}]={record[key]}"
    return output

