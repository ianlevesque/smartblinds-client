import typing

from auth0.v3.authentication import Database
import requests
import base64


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Blind:
    def __init__(self, name: str, encoded_mac: str, room_id: str, encoded_passkey: str):
        self.name = name
        self.encoded_mac = encoded_mac
        self.room_id = room_id
        self.encoded_passkey = encoded_passkey

    @property
    def mac_address(self):
        return base64.b64decode(self.encoded_mac)

    @property
    def passkey(self):
        return base64.b64decode(self.encoded_passkey)

    def __repr__(self):
        return "Blind(name='%s',encoded_mac='%s',room_id='%s',encoded_passkey='%s')" % (
            self.name,
            self.encoded_mac,
            self.room_id,
            self.encoded_passkey,
        )


class BlindState:
    def __init__(self, position: int, rssi: int, battery_level: int):
        self.position = position
        self.rssi = rssi
        self.battery_level = battery_level

    def __repr__(self):
        return "BlindState(position=%d,rssi=%d,battery_level=%d)" % (
            self.position,
            self.rssi,
            self.battery_level,
        )


class Room:
    def __init__(self, name: str, uuid: str, open_position: float, close_position: float, blinds: [Blind] = None):
        self.name = name
        self.uuid = uuid
        self.open_position = open_position
        self.close_position = close_position
        self.blinds = blinds or []

    def __repr__(self):
        return "Room(name='%s',uuid='%s',open_position=%f,close_position=%f,blinds=%s)" % (
            self.name,
            self.uuid,
            self.open_position,
            self.close_position,
            self.blinds,
        )


class SmartBlindsClient:
    AUTH0_DOMAIN = "mysmartblinds.auth0.com"
    AUTH0_CLIENT_ID = "1d1c3vuqWtpUt1U577QX5gzCJZzm8WOB"
    AUTH0_CONNECTION = "Username-Password-Authentication"

    GRAPHQL_ENDPOINT = "https://api.mysmartblinds.com/v1/graphql"

    BATCH_SIZE = 7

    def __init__(self, username: str, password: str):
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

    def get_blinds_and_rooms(self) -> typing.Tuple[typing.List[Blind], typing.List[Room]]:
        """ Get all configured rooms and their blinds """
        response = self._graphql(
            query='''
                query GetUserInfo {
                    user {
                        rooms {
                            id
                            name
                            defaultClosePosition
                            defaultOpenPosition
                            deleted
                        }
                        blinds {
                            name
                            encodedMacAddress
                            encodedPasskey
                            roomId
                            deleted
                        }
                    }
                }
            ''')

        rooms = {}
        blinds = []

        for room in response['data']['user']['rooms']:
            if not room['deleted']:
                rooms[room['id']] = Room(
                    room['name'],
                    room['id'],
                    room['defaultOpenPosition'],
                    room['defaultClosePosition'],
                )

        for blind in response['data']['user']['blinds']:
            if not blind['deleted']:
                blind = Blind(blind['name'], blind['encodedMacAddress'], blind['roomId'], blind['encodedPasskey'])
                blinds.append(blind)

                if blind.room_id is not None and blind.room_id in rooms:
                    room = rooms[blind.room_id]
                    room.blinds.append(blind)

        return blinds, list(rooms.values())

    def get_blinds_state(self, blinds: [Blind]) -> typing.Mapping[str, BlindState]:
        blind_states = {}
        for blinds_batch in chunks(blinds, self.BATCH_SIZE):
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
                    'blinds': list(map(lambda b: b.encoded_mac, blinds)),
                })
            blind_states.update(self._parse_states(response))

        return blind_states

    def set_blinds_position(self, blinds: [Blind], position: int) -> typing.Mapping[str, BlindState]:
        blind_states = {}
        for blinds_batch in chunks(blinds, self.BATCH_SIZE):
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
                    'blinds': list(map(lambda b: b.encoded_mac, blinds_batch)),
                })
            blind_states.update(self._parse_states(response, 'updateBlindsPosition'))

        return blind_states

    @staticmethod
    def _parse_states(response, key='blindsState') -> typing.Mapping[str, BlindState]:
        blind_states = {}

        for blind_state in response['data'][key]:
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

    def _auth_header(self) -> str:
        if self._tokens is None:
            self.login()

        if self._tokens["token_type"] != "bearer":
            raise Exception("Not a bearer token")

        if "id_token" not in self._tokens:
            raise Exception("No id_token")

        return "Bearer %s" % self._tokens["id_token"]
