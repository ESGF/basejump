import requests
import openid.fetchers


class RequestsFetcher(openid.fetchers.HTTPFetcher):
    """
    Implements the fetcher API from python-openid

    You can choose to use this fetcher and pass in your cert for SSL compliance.
    """
    def __init__(self, no_verify=False, cert_path=None):
        self.verify = True

        if no_verify:
            self.verify = False

        if cert_path is not None:
            self.verify = cert_path

    def fetch(self, url, body=None, headers=None):
        if body is None:
            resp = requests.get(url, headers=headers, verify=self.verify)
        else:
            resp = requests.post(url, data=body, headers=headers, verify=self.verify)

        formatted_response = openid.fetchers.HTTPResponse()
        formatted_response.body = resp.text
        formatted_response.final_url = resp.url
        formatted_response.headers = resp.headers
        formatted_response.status = resp.status_code

        return formatted_response
