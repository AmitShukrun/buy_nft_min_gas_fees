import requests
from datetime import datetime
from flask import Flask, jsonify, render_template
from config import etherscan_api_key, es_api_key, es_cloud_id
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


app = Flask(__name__)


# Creating an Elasticsearch client
es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)


# Check if the connection is successful
if es.ping():
    print("Connected to Elasticsearch successfully.")


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


def save_the_data_in_es_db(gas_fee_data):
    index_name = "gas_fee_data_index"

    # We'll create the index if it does not exist
    if not es.indices.exists(index=index_name):
        # Create the index
        es.indices.create(index=index_name)

        # Prepare bulk data
        bulk_data = [{"_index": index_name, "_source": transaction} for transaction in gas_fee_data]

        # Index the gas fee data into Elasticsearch
        bulk(es, bulk_data)


@app.route('/eth_to_usd')
def eth_to_usd():
    """ This function returns the current ETH to USD exchange rate """

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

    # I take only the last 1000 transactions in order to display the chart nicely and not too crowded
    transactions = gas_fee_data['result'][-1000:]

    if gas_fee_data and gas_fee_data.get("status") == "1":
        gas_fee_list = []
        for transaction in transactions:
            gas_price_wei = int(transaction.get("gasPrice"))
            gas_price_eth = gas_price_wei / 10**18  # Convert gas price from Wei to ETH
            gas_fee_usd = gas_price_eth * eth_to_usd_rate  # Convert gas price from Ether to USD
            date = convert_timestamp_to_date(int(transaction['timeStamp']))

            gas_fee_list.append({'date': date, 'gas_fee_usd': f"{gas_fee_usd:.8f}"})

        save_the_data_in_es_db(gas_fee_list)  # Save the data into Elasticsearch DB

        return render_template('gas_fee_chart.html', gas_fee_list=gas_fee_list)

    else:
        return jsonify({'error': 'Failed to fetch gas fee data or API key is invalid.'}), 500


if __name__ == "__main__":
    app.run(debug=True)
