"""Define tests for switch module."""

import json
from unittest.mock import AsyncMock, patch

from pyatmo import DeviceType
from pyatmo.modules.device_types import DeviceCategory
from tests.common import MockResponse, load_fixture


async def test_async_switch_NLP(async_home):
    """Test NLP Legrand plug."""
    module_id = "12:34:56:80:00:12:ac:f2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLP
    assert module.firmware_revision == 62
    assert module.on
    assert module.power == 0


async def test_offload_meters(async_home):
    """offload_meters (smart-shedder ids) are parsed on offload modules."""
    module = async_home.modules["12:34:56:80:00:12:ac:f2"]
    assert module.offload_meters == ["98:76:54:32:10:ab"]


async def test_offload_meters_absent(async_home):
    """offload_meters is None when the field is absent from the response."""
    module = async_home.modules["12:34:56:00:01:01:01:b7"]
    assert module.offload_meters is None


async def test_offload_meters_empty(async_home):
    """offload_meters is an empty list when the API reports no shedders."""
    module = async_home.modules["12:34:56:80:60:40"]
    assert module.offload_meters == []


async def test_async_switch_NLF(async_home):
    """Test NLF Legrand dimmer."""
    module_id = "00:11:22:33:00:11:45:fe"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLF
    assert module.firmware_revision == 57
    assert module.on is False
    assert module.brightness == 63
    assert module.power == 0


async def test_async_switch_NLIS(async_home):
    """Test NLIS Legrand module."""
    module_id = "12:34:56:00:01:01:01:b6"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category is None
    assert module.reachable is True
    module_id = "12:34:56:00:01:01:01:b6#1"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category == DeviceCategory.switch
    # The API reports `reachable` only on the parent entry, so the gangs
    # inherit it. See home-assistant/core#178403.
    assert module.reachable is True
    module_id = "12:34:56:00:01:01:01:b6#2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category == DeviceCategory.switch
    assert module.reachable is True


async def test_async_switch_NLIS_follows_parent_unreachable(async_account):
    """NLIS gangs report unreachable once the parent module does."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]

    parent_id = "12:34:56:00:01:01:01:b6"
    assert home.modules[f"{parent_id}#1"].reachable is True

    homestatus = json.loads(load_fixture("homestatus_91763b24c43d3e344f424e8b.json"))
    for raw_module in homestatus["body"]["home"]["modules"]:
        if raw_module["id"] == parent_id:
            raw_module["reachable"] = False

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(homestatus, 200)),
    ):
        await async_account.async_update_status(home_id)

    assert home.modules[parent_id].reachable is False
    assert home.modules[f"{parent_id}#1"].reachable is False
    assert home.modules[f"{parent_id}#2"].reachable is False


async def test_async_switch_NLIS_reachable_again_after_bridge_error(
    async_account_multi,
):
    """NLIS gangs recover once their bridge stops being reported in errors[].

    The Legrand gateway of the multi home lists the `#`-suffixed gangs in
    `modules_bridged`, and the gangs themselves never report `reachable`. An
    error on the bridge must therefore not pin them unreachable for good.
    See home-assistant/core#178403.
    """
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"
    bridge_id = "aa:aa:aa:aa:aa:aa"
    parent_id = "98:76:54:32:10:00:00:24"
    gang_ids = [f"{parent_id}#1", f"{parent_id}#2"]
    home = async_account_multi.homes[home_id]
    # The gangs are bridged children of the gateway, not only of their parent.
    assert set(gang_ids) <= set(home.modules[bridge_id].modules)

    # The gangs report their own state, but never `reachable`.
    gang_status = [
        {"id": gang_id, "type": "NLIS", "on": True, "power": 0} for gang_id in gang_ids
    ]
    healthy = {
        "status": "ok",
        "body": {
            "home": {
                "id": home_id,
                "modules": [
                    {"id": bridge_id, "type": "NLG", "reachable": True},
                    {"id": parent_id, "type": "NLIS", "reachable": True},
                    *gang_status,
                ],
            },
        },
    }
    outage = {
        "status": "ok",
        "body": {
            "home": {"id": home_id, "modules": gang_status},
            "errors": [{"code": 3, "id": bridge_id}],
        },
    }

    async def poll(payload):
        with patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            AsyncMock(return_value=MockResponse(payload, 200)),
        ):
            await async_account_multi.async_update_status(home_id)

    await poll(healthy)
    assert [home.modules[gang_id].reachable for gang_id in gang_ids] == [True, True]

    await poll(outage)
    assert home.modules[bridge_id].reachable is False
    assert home.modules[parent_id].reachable is False
    assert [home.modules[gang_id].reachable for gang_id in gang_ids] == [False, False]

    await poll(healthy)
    assert home.modules[bridge_id].reachable is True
    assert home.modules[parent_id].reachable is True
    assert [home.modules[gang_id].reachable for gang_id in gang_ids] == [True, True]
