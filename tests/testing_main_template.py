import asyncio

from aiohttp import ClientSession

import pyatmo
from pyatmo.auth import AbstractAsyncAuth
from pyatmo.modules.module import MeasureInterval

MY_TOKEN_FROM_NETATMO = "MY_TOKEN"


class MyAuth(AbstractAsyncAuth):
    async def async_get_access_token(self):
        return MY_TOKEN_FROM_NETATMO


async def main():
    session = ClientSession()
    async_auth = MyAuth(session)
    account = pyatmo.AsyncAccount(async_auth)

    t = asyncio.create_task(account.async_update_topology())
    home_id = "MY_HOME_ID"
    module_id = "MY_MODULE_ID"

    await asyncio.gather(t)

    await account.async_update_status(home_id=home_id)

    strt = 1709766000 + 10 * 60
    end = 1709852400 + 10 * 60
    await account.async_update_measures(
        home_id=home_id,
        module_id=module_id,
        interval=MeasureInterval.HALF_HOUR,
        start_time=strt,
        end_time=end,
    )


if __name__ == "__main__":
    topology = asyncio.run(main())
