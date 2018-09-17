import typing
from dataclasses import dataclass

from auth0.v3.authentication import Database
import requests


@dataclass
class Blind:
    name: str
    encoded_mac: str


@dataclass
class BlindState:
    position: int
    rssi: int
    battery_level: int


class SmartBlindsClient:
    AUTH0_DOMAIN = "mysmartblinds.auth0.com"
    AUTH0_CLIENT_ID = "1d1c3vuqWtpUt1U577QX5gzCJZzm8WOB"
    AUTH0_CONNECTION = "Username-Password-Authentication"

    GRAPHQL_ENDPOINT = "https://api.mysmartblinds.com/v1/graphql"

    _username: str
    _password: str
    _tokens: typing.Mapping[str, str]

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._tokens = None

    def login(self):
        auth0database = Database(self.AUTH0_DOMAIN)
        self._tokens = auth0database.login(self.AUTH0_CLIENT_ID, self._username, self._password,
                                           self.AUTH0_CONNECTION,
                                           device="smartblinds_client",
                                           scope="openid offline_access")

        return self._tokens

    def get_blinds(self):
        """ Get all configured blinds """
        response = self._graphql(
            query='''
                query GetUserInfo {
                    user {
                        blinds {
                            name
                            encodedMacAddress
                        }
                    }
                }
            ''')

        blinds = []

        for blind in response['data']['user']['blinds']:
            blinds.append(Blind(blind['name'], blind['encodedMacAddress']))

        return blinds

    def get_blinds_state(self, blinds: [Blind]) -> typing.Mapping[str, BlindState]:
        response = self._graphql(
            query='''
                query GetBlindsState($blinds: [String]) {
                    blindsState(encodedMacAddresses: $blinds) {
                        encodedMacAddress
                        position
                        rssi
                        batteryLevel
                    }
                }
            ''',
            variables={
                'blinds': list(map(lambda b: b.encoded_mac, blinds))
            })

        return self._parse_states(response)

    def set_blinds_position(self, blinds: [Blind], position: int):
        response = self._graphql(
            query='''
                mutation UpdateBlindsPosition($blinds: [String], $position: Int!) {
                    updateBlindsPosition(encodedMacAddresses: $blinds, position: $position) {
                        encodedMacAddress
                        position
                        rssi
                        batteryLevel
                    }
                }        
            ''',
            variables={
                'position': position,
                'blinds': list(map(lambda b: b.encoded_mac, blinds))
            })

        return self._parse_states(response)

    @staticmethod
    def _parse_states(response) -> typing.Mapping[str, BlindState]:
        blind_states = {}

        for blind_state in response['data']['blindsState']:
            blind_states[blind_state['encodedMacAddress']] = BlindState(
                position=blind_state['position'],
                rssi=blind_state['rssi'],
                battery_level=blind_state['batteryLevel'])

        return blind_states

    def _graphql(self, query, variables=None):
        response = requests.post(
            self.GRAPHQL_ENDPOINT,
            headers={
                'Authorization': self._auth_header(),
            },
            json={
                'query': query,
                'variables': variables
            }
        )

        response.raise_for_status()
        return response.json()

    def _auth_header(self):
        if self._tokens is None:
            self.login()

        if self._tokens["token_type"] != "bearer":
            raise Exception("Not a bearer token")

        if "id_token" not in self._tokens:
            raise Exception("No id_token")

        return "Bearer %s" % self._tokens["id_token"]
