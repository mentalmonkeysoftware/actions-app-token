from collections import namedtuple, Counter
from github3 import GitHub
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import time
import json
import jwt
import requests
from typing import List
import os

class GitHubApp(GitHub):
    """
    This is a small wrapper around the github3.py library
    
    Provides some convenience functions for testing purposes.
    """
    
    def __init__(self, pem_path, app_id, nwo):
        super().__init__()
        self.app_id = app_id

        self.path = Path(pem_path)
        self.app_id = app_id
        if not self.path.is_file():
            raise ValueError(f'argument: `pem_path` must be a valid filename. {pem_path} was not found.')
        self.nwo = nwo
    
    def get_app(self):
        with open(self.path, 'rb') as key_file:
            client = GitHub()
            client.login_as_app(private_key_pem=key_file.read(),
                                app_id=self.app_id)
        return client
    
    def get_installation(self, installation_id):
        "Login as app installation without requesting previously gathered data."
        with open(self.path, 'rb') as key_file:
            client = GitHub()
            client.login_as_app_installation(private_key_pem=key_file.read(),
                                             app_id=self.app_id,
                                             installation_id=installation_id)
        return client
        
    def get_test_installation_id(self):
        "Get a sample test_installation id."
        client = self.get_app()
        return next(client.app_installations()).id
        
    def get_test_installation(self):
        "Login as app installation with the first installation_id retrieved."
        return self.get_installation(self.get_test_installation_id())
    
    def get_test_repo(self):
        repo = self.get_all_repos(self.get_test_installation_id())[0]
        appInstallation = self.get_test_installation()
        owner, name = repo['full_name'].split('/')
        return appInstallation.repository(owner, name)
        
    def get_test_issue(self):
        test_repo = self.get_test_repo()
        return next(test_repo.issues())
        
    def get_jwt(self):
        """
        This is needed to retrieve the installation access token (for debugging). 
        
        Useful for debugging purposes.
        """
        now = self._now_int()
        payload = {
            "iat": now,
            "exp": now + 60,
            "iss": self.app_id
        }
        with open(self.path, 'rb') as key_file:
            # Load the PEM private key using the new function.
            private_key = load_pem_private_key(key_file.read(), password=None)
            token = jwt.encode(payload, private_key, algorithm='RS256')
            return token
    
    def get_installation_id(self):
        "https://developer.github.com/v3/apps/#find-repository-installation"

        owner, repo = self.nwo.split('/')

        url = f'https://api.github.com/repos/{owner}/{repo}/installation'

        # Ensure the JWT is a string (PyJWT may return bytes in some versions)
        jwt_token = self.get_jwt()
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode()
            
        headers = {'Authorization': f'Bearer {jwt_token}',
                   'Accept': 'application/vnd.github.machine-man-preview+json'}
        
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            raise Exception(f'Status code: {response.status_code}, {response.json()}')
        return response.json()['id']

    def get_installation_access_token(self, installation_id):
        "Get the installation access token for debugging."
        
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        jwt_token = self.get_jwt()
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode()
        headers = {'Authorization': f'Bearer {jwt_token}',
                   'Accept': 'application/vnd.github.machine-man-preview+json'}
        
        response = requests.post(url=url, headers=headers)
        if response.status_code != 201:
            raise Exception(f'Status code: {response.status_code}, {response.json()}')
        return response.json()['token']

    def _extract(self, d, keys):
        "Extract selected keys from a dict."
        return dict((k, d[k]) for k in keys if k in d)
    
    def _now_int(self):
        return int(time.time())

    def get_all_repos(self, installation_id):
        """Get all repos that this installation has access to.
        
        Useful for testing and debugging.
        """
        url = 'https://api.github.com/installation/repositories'
        token = self.get_installation_access_token(installation_id)
        headers = {'Authorization': f'token {token}',
                   'Accept': 'application/vnd.github.machine-man-preview+json'}
        
        response = requests.get(url=url, headers=headers)
        
        if response.status_code >= 400:
            raise Exception(f'Status code: {response.status_code}, {response.json()}')
        
        fields = ['name', 'full_name', 'id']
        return [self._extract(x, fields) for x in response.json()['repositories']]

    def generate_installation_curl(self, endpoint):
        iat = self.get_installation_access_token(self.get_test_installation_id())
        print(f'curl -i -H "Authorization: token {iat}" -H "Accept: application/vnd.github.machine-man-preview+json" https://api.github.com{endpoint}')

if __name__ == '__main__':
    
    pem_path = 'pem.txt'
    app_id = os.getenv('INPUT_APP_ID')
    nwo = os.getenv('GITHUB_REPOSITORY')

    assert pem_path, 'Must supply input APP_PEM'
    assert app_id, 'Must supply input APP_ID'
    assert nwo, "The environment variable GITHUB_REPOSITORY was not found."

    app = GitHubApp(pem_path=pem_path, app_id=app_id, nwo=nwo)
    installation_id = app.get_installation_id()
    token = app.get_installation_access_token(installation_id=installation_id)
    assert token, 'Token not returned!'

    # Mask the token to prevent accidental logging
    print(f"::add-mask::{token}")

    # Write token to GITHUB_ENV so it's available to later steps
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a') as env_file:
            env_file.write(f"APP_TOKEN={token}\n")
    else:
        print("⚠️ Warning: GITHUB_ENV is not set!")        
