# https://developer.bitcoin.org/devguide/mining.html
# also interesting: https://github.com/frenow/Python_miner_btc/tree/master/MiniMiner and https://github.com/Pymmdrza/SoloMinerV2

import blkbuilder
import json
import struct
import sys
import subprocess
from coinbase_tx import create_coinbase
import threading
import pathlib


def bitcoin_cli(message, command="getblocktemplate", verbose=0, bitcoin_cli=r"C:\Programme\Bitcoin\daemon\bitcoin-cli"):
	if verbose == 1:
		print("request sent: ")
		print(json.dumps(message, indent=4))

	if message is not None:
		if not isinstance(message, str):
			message = json.dumps(message)
		process = subprocess.run([bitcoin_cli, command, message], stdout=subprocess.PIPE)
	else:
		process = subprocess.run([bitcoin_cli, command], stdout=subprocess.PIPE)
	blocktemplate = json.loads(process.stdout.decode('utf-8'))
	if verbose == 1:
		print("response received: ")
		print(json.dumps(blocktemplate, indent=4))
	return blocktemplate

	# # sample response
	# with open('sample_response.json', 'r') as f:
	# 	return json.loads(f.read())

def create_template(extranonce, addr="3DJJuWJdWwxd7N3kJUXS8XZ2MhRA6X7Z4g"):
	req = {"rules": ["segwit"]}
	blocktemplate = bitcoin_cli(message=req, command="getblocktemplate")
	coinbase = {}
	coinbase['data'] = create_coinbase(
			coinbase_value=blocktemplate["coinbasevalue"],
			coinbase_text=str(extranonce).encode().hex(),
			block_height=blocktemplate['height'],
			wallet_address=addr,
		)
	blocktemplate['coinbasetxn'] = coinbase

	tmpl = blkbuilder.Template()
	tmpl.add(blocktemplate)
	
	return tmpl


def get_blockcount(check_interval=30.0):
	global blockcount
	blockcount = bitcoin_cli(None, "getblockcount")
	sys.stdout.write("blockcount: " + str(blockcount) + "       \r\n")
	sys.stdout.flush()
	threading.Timer(check_interval, get_blockcount).start()

# recursive implementation of mining loop
def mine(tmpl):
	global blockcount, extranonce
	nonce = 0
	data = tmpl.get_data()
	assert(len(data) >= 76)
	while nonce < 0x7fffffff and tmpl.height == blockcount + 1:
		data = data[:76] + struct.pack('!I', nonce)
		blkhash = blkbuilder.dblsha256(data)
		if blkhash <= tmpl.target:
			print("Found nonce: 0x%8x \n" % nonce)
			mined_block = tmpl.submit(data, nonce)
			f = open("mined_block.txt", "w")
			f.write(mined_block)
			f.close()
			path_to_blk = str(pathlib.Path().resolve()) + "\\mined_block.txt"
			bitcoin_cli(message=path_to_blk, command="submitblock", verbose=1)
			break
		if (not (nonce % 0x1000)):
			sys.stdout.write("0x%8x hashes done...\r" % nonce)
			sys.stdout.flush()
		nonce += 1
	
	if nonce >= 0x7fffffff:
		extranonce += 1
		sys.stdout.write("\nextranonce increased to: " + str(extranonce) + "       \r\n")
		sys.stdout.flush()
	else:
		extranonce = 0
		sys.stdout.write(f"\nstarting to mine new block (height:{str(blockcount + 1)})\r\n")
		sys.stdout.flush()
	tmpl = create_template(extranonce)
	print("\n")
	mine(tmpl)

if __name__ == "__main__":
	# start blockcount thread
	get_blockcount()
	extranonce = 0
	tmpl = create_template(extranonce)
	# start mining loop
	mine(tmpl)

