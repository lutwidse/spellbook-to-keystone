from aiohttp import ClientSession, TCPConnector
import asyncio
import json
import glob
import re
import os
from tenacity import retry, wait_fixed


@retry(wait=wait_fixed(1))
async def fetch_abi(session, url, proxies):
    async with session.get(url, proxy=proxies["http"]) as response:
        return await response.json()


@retry(wait=wait_fixed(1))
async def fetch_and_write_abi(session, define, proxies):
    chain = define[0]
    address = define[1]
    name_contract = define[3]

    if os.path.exists(f'self_define/{address}.json'):
        return

    if chain == 'Project':
        return

    url = ""
    if chain == 'ethereum':
        url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={address}"
    elif chain == 'bnb':
        url = f"https://api.bscscan.com/api?module=contract&action=getabi&address={address}"
    elif chain == 'polygon':
        url = f"https://api.polygonscan.com/api?module=contract&action=getabi&address={address}"
    elif chain == 'arbitrum':
        url = f"https://api.arbiscan.io/api?module=contract&action=getabi&address={address}"
    elif chain == 'optimism':
        url = f"https://api-optimistic.etherscan.io/api?module=contract&action=getabi&address={address}"
    elif chain == 'base':
        url = f"https://api.basescan.org/api?module=contract&action=getabi&address={address}"

    result = await fetch_abi(session, url, proxies)
    abi = result['result']

    if abi == 'Contract source code not verified':
        return
    elif abi == 'Max rate limit reached, please use API Key for higher rate limit':
        raise Exception(
            'Max rate limit reached, please use API Key for higher rate limit')

    abi = json.loads(abi)

    data = {
        "address": address,
        "name": name_contract,
        "metadata": {
            "output": {
                "abi": abi
            }
        }
    }

    with open(f'self_define/{address}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


async def main():
    proxy_host = "redacted"
    proxy_port = "redacted"
    proxy_auth = "redacted"
    proxies = {
        "http": f"http://{proxy_auth}@{proxy_host}:{proxy_port}/",
        "https": f"https://{proxy_auth}@{proxy_host}:{proxy_port}/",
    }

    sql_files = glob.glob('spellbook/models/**/*.sql', recursive=True)
    pattern = r"\('(\w+)',\s(0x[\da-fA-F]{40}),\s'([^']*)',\s'([^']*)'\)"
    defines = set()

    for file in sql_files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(pattern, content)
            for match in matches:
                define = (match[0], match[1], match[2], match[3])
                if (match[0], match[1]) not in defines and not os.path.exists(f'self_define/{match[1]}.json') and match[0] != 'Project':
                    defines.add(define)

    connector = TCPConnector(limit=10)
    async with ClientSession(connector=connector) as session:
        tasks = [fetch_and_write_abi(session, define, proxies)
                 for define in defines]
        await asyncio.gather(*tasks)

asyncio.run(main())
