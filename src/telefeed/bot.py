from aiohttp import ClientSession as BaseSession
from aiosocksy import Socks5Auth
from aiosocksy.connector import ProxyConnector, ProxyClientRequest
from aiotg import Bot as BaseBot


class Session(BaseSession):
    def __init__(self, *args, proxy_auth=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__proxy_auth = proxy_auth

    async def _request(self, *args, **kwargs):
        return await super()._request(*args, **kwargs, proxy_auth=self.__proxy_auth)


class Bot(BaseBot):
    def __init__(self, *args, proxy=None, **kwargs):
        self.__proxy_socks5 = proxy and proxy.startswith('socks5://')
        self.__proxy_socks5_auth = None
        if self.__proxy_socks5:
            if '@' in proxy:
                proxy_auth, proxy = proxy[9:].split('@')
                proxy = 'socks5://{}'.format(proxy)
                proxy_user, proxy_pass = proxy_auth.split(':')
                self.__proxy_socks5_auth = Socks5Auth(proxy_user, password=proxy_pass)
        super().__init__(*args, proxy=proxy, **kwargs)

    @property
    def session(self):
        if self.__proxy_socks5:
            if not self._session or self._session.closed:
                self._session = Session(
                    connector=ProxyConnector(),
                    json_serialize=self.json_serialize,
                    request_class=ProxyClientRequest,
                    proxy_auth=self.__proxy_socks5_auth
                )
            return self._session
        return super().session
