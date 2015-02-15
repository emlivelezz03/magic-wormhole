import time, requests, json
from binascii import hexlify, unhexlify
from spake2 import SPAKE2_A, SPAKE2_B
from nacl.secret import SecretBox
from nacl import utils
from . import codes
from .hkdf import HKDF
from .const import RELAY

SECOND = 1
MINUTE = 60*SECOND

class Timeout(Exception):
    pass

# POST /allocate                                  -> {channel-id: INT}
# POST /CHANNEL-ID/SIDE/pake/post  {message: STR} -> {messages: [STR..]}
# POST /CHANNEL-ID/SIDE/pake/poll                 -> {messages: [STR..]}
# POST /CHANNEL-ID/SIDE/data/post  {message: STR} -> {messages: [STR..]}
# POST /CHANNEL-ID/SIDE/data/poll                 -> {messages: [STR..]}
# POST /CHANNEL-ID/SIDE/deallocate                -> waiting | deleted

class Common:
    def url(self, suffix):
        return "%s%d/%s/%s" % (self.relay, self.channel_id, self.side, suffix)

    def poll(self, msgs, url_suffix):
        while not msgs:
            if time.time() > (self.started + self.timeout):
                raise Timeout
            time.sleep(self.wait)
            r = requests.post(self.url(url_suffix))
            r.raise_for_status()
            msgs = r.json()["messages"]
        return msgs

    def _allocate(self):
        r = requests.post(self.relay + "allocate")
        r.raise_for_status()
        channel_id = r.json()["channel-id"]
        return channel_id

    def _post_pake(self):
        msg = self.sp.start()
        post_data = {"message": hexlify(msg).decode("ascii")}
        r = requests.post(self.url("pake/post"), data=json.dumps(post_data))
        r.raise_for_status()
        other_msgs = r.json()["messages"]
        return other_msgs

    def _poll_pake(self, other_msgs):
        msgs = self.poll(other_msgs, "pake/poll")
        pake_msg = unhexlify(msgs[0].encode("ascii"))
        key = self.sp.finish(pake_msg)
        return key

    def _encrypt_data(self, key, data):
        assert len(key) == SecretBox.KEY_SIZE
        box = SecretBox(key)
        nonce = utils.random(SecretBox.NONCE_SIZE)
        return box.encrypt(self.data, nonce)

    def _post_data(self, data):
        post_data = json.dumps({"message": hexlify(data).decode("ascii")})
        r = requests.post(self.url("data/post"), data=post_data)
        r.raise_for_status()
        other_msgs = r.json()["messages"]
        return other_msgs

    def _poll_data(self, other_msgs):
        msgs = self.poll(other_msgs, "data/poll")
        data = unhexlify(msgs[0].encode("ascii"))
        return data

    def _decrypt_data(self, key, encrypted):
        assert len(key) == SecretBox.KEY_SIZE
        box = SecretBox(key)
        data = box.decrypt(encrypted)
        return data

    def _deallocate(self):
        r = requests.post(self.url("deallocate"))
        r.raise_for_status()

class Initiator(Common):
    def __init__(self, appid, data, relay=RELAY):
        self.appid = appid
        self.data = data
        assert relay.endswith("/")
        self.relay = relay
        self.started = time.time()
        self.wait = 0.5*SECOND
        self.timeout = 3*MINUTE
        self.side = "initiator"

    def get_code(self):
        self.channel_id = self._allocate() # allocate channel
        self.code = codes.make_code(self.channel_id)
        self.sp = SPAKE2_A(self.code.encode("ascii"),
                           idA=self.appid+":Initiator",
                           idB=self.appid+":Receiver")
        self._post_pake()
        return self.code

    def get_data(self):
        key = self._poll_pake([])
        try:
            outbound_key = HKDF(key, SecretBox.KEY_SIZE, CTXinfo=b"sender")
            outbound_encrypted = self._encrypt_data(outbound_key, self.data)
            other_msgs = self._post_data(outbound_encrypted)

            inbound_encrypted = self._poll_data(other_msgs)
            inbound_key = HKDF(key, SecretBox.KEY_SIZE, CTXinfo=b"receiver")
            inbound_data = self._decrypt_data(inbound_key, inbound_encrypted)
        finally:
            self._deallocate()
        return inbound_data


class Receiver(Common):
    def __init__(self, appid, data, relay=RELAY):
        self.appid = appid
        self.data = data
        self.relay = relay
        assert relay.endswith("/")
        self.started = time.time()
        self.wait = 0.5*SECOND
        self.timeout = 3*MINUTE
        self.side = "receiver"
        self.code = None
        self.channel_id = None

    def list_channels(self):
        r = requests.get(self.relay + "list")
        r.raise_for_status()
        channel_ids = r.json()["channel-ids"]
        return channel_ids

    def input_code(self, prompt="Enter wormhole code: "):
        channel_ids = self.list_channels()
        code = codes.input_code_with_completion(prompt, channel_ids)
        return code

    def set_code(self, code):
        assert self.code is None
        assert self.channel_id is None
        self.code = code
        self.channel_id = codes.extract_channel_id(code)
        self.sp = SPAKE2_B(code.encode("ascii"),
                           idA=self.appid+":Initiator",
                           idB=self.appid+":Receiver")

    def get_data(self):
        assert self.code is not None
        assert self.channel_id is not None
        other_msgs = self._post_pake()
        key = self._poll_pake(other_msgs)

        try:
            outbound_key = HKDF(key, SecretBox.KEY_SIZE, CTXinfo=b"receiver")
            outbound_encrypted = self._encrypt_data(outbound_key, self.data)
            other_msgs = self._post_data(outbound_encrypted)

            inbound_encrypted = self._poll_data(other_msgs)
            inbound_key = HKDF(key, SecretBox.KEY_SIZE, CTXinfo=b"sender")
            inbound_data = self._decrypt_data(inbound_key, inbound_encrypted)
        finally:
            self._deallocate()
        return inbound_data