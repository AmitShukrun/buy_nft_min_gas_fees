import requests
from datetime import datetime
from flask import Flask, jsonify
from config import etherscan_api_key


app = Flask(__name__)


def get_eth_to_usd_exchange_rate():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "ethereum",
        "vs_currencies": "usd",
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            exchange_rate_data = response.json()
            eth_to_usd_rate = exchange_rate_data.get("ethereum").get("usd")
            return eth_to_usd_rate
        else:
            print(f"Failed to retrieve ETH to USD exchange rate. Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return None


def get_gas_fee_data(contract_address, api_key):
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": contract_address,
        "sort": "desc",
        "apikey": api_key,
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            gas_fee_data = response.json()
            return gas_fee_data
        else:
            print(f"Failed to retrieve data. Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return None


def convert_timestamp_to_date(timestamp):
    try:
        date_time_obj = datetime.fromtimestamp(timestamp)  # Convert timestamp to a datetime object
        formatted_date = date_time_obj.strftime("%Y-%m-%d %H:%M:%S")[:-3]  # Format the datetime object

        return formatted_date

    except ValueError:
        return "Invalid timestamp"


@app.route('/eth_to_usd')
def eth_to_usd():
    eth_to_usd_rate = get_eth_to_usd_exchange_rate()
    if eth_to_usd_rate:
        return jsonify({'exchange_rate': eth_to_usd_rate})
    else:
        return jsonify({'error': 'Failed to retrieve ETH to USD exchange rate.'}), 500


@app.route('/calc_gas_fee_data')
def calc_gas_fee_data():
    contract = "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB"
    api_key = etherscan_api_key  # For information security

    eth_to_usd_rate = get_eth_to_usd_exchange_rate()
    gas_fee_data = get_gas_fee_data(contract, api_key)

    if gas_fee_data and gas_fee_data.get("status") == "1":
        gas_fee_list = []
        for transaction in gas_fee_data.get("result"):
            gas_price_wei = int(transaction.get("gasPrice"))
            gas_price_eth = gas_price_wei / 10**18  # Convert gas price from Wei to ETH
            gas_fee_usd = gas_price_eth * eth_to_usd_rate  # Convert gas price from Ether to USD
            date = convert_timestamp_to_date(int(transaction['timeStamp']))

            gas_fee_list.append({'date': date, 'gas_fee_usd': f"{gas_fee_usd:.8f}"})

        return jsonify({'gas_fee_data': gas_fee_list})
    else:
        return jsonify({'error': 'Failed to fetch gas fee data or API key is invalid.'}), 500


if __name__ == "__main__":
    app.run(debug=True)
