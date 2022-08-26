from binascii import a2b_hex
from binascii import b2a_hex
from time import time
from hashlib import sha256
from struct import pack


def dblsha256(data):
	return sha256(sha256(data).digest()).digest()


class Transaction:
	def __init__(self, txn = {}):
		if txn is None:
			return
		if 'data' not in txn:
			raise ValueError("Missing or invalid type for transaction data")
		self.data = a2b_hex(txn['data'])


class Template:
	def __init__(self):
		self.sigoplimit = 0xffff
		self.sizelimit = 0xffffffff
		self.maxtime = 0xffffffff
		self.maxtimeoff = 0x7fff
		self.mintime = 0
		self.mintimeoff = -0x7fff
		self.cbtxn = None
		self.version = None


	def get_data(self, usetime = None):
		if usetime is None: usetime = time()

		cbuf = pack('<I', self.version)
		cbuf += self.prevblk
		
		if not self.cbtxn.data:
			return None
		
		merkleroot = self.build_merkle_root()
		if not merkleroot:
			return None
		cbuf += merkleroot
		
		cbuf += pack('<I', self.curtime)
		cbuf += self.diffbits

		if cbuf is None:
			return None
		
		cbuf = cbuf[:68] + self.set_times(usetime) + cbuf[68+4:]
		
		return cbuf


	def build_merkle_root(self):
		if not self.build_merkle_branches():
			return None
		
		lhs = dblsha256(self.cbtxn.data)
		
		for rhs in self._mrklbranch:
			lhs = dblsha256(lhs + rhs)
		
		return lhs


	def build_merkle_branches(self):
		if hasattr(self, '_mrklbranch'):
			return True
		
		if not self.hash_transactions():
			return False
		
		branchcount = len(self.txns).bit_length()
		branches = []
		
		merklehashes = [None] + [txn.hash_ for txn in self.txns]
		while len(branches) < branchcount:
			branches.append(merklehashes[1])
			if len(merklehashes) % 2:
				merklehashes.append(merklehashes[-1])
			merklehashes = [None] + [dblsha256(merklehashes[i] + merklehashes[i + 1]) for i in range(2, len(merklehashes), 2)]
		
		self._mrklbranch = branches
		
		return True


	def hash_transactions(self):
		for txn in self.txns:
			if hasattr(txn, 'hash_'):
				continue
			txn.hash_ = dblsha256(txn.data)
		return True


	def set_times(self, usetime = None):
		# usetime: time when get_data is called
		# _time_rcvd: time when block was added to template
		time_passed = int(usetime - self._time_rcvd)
		timehdr = self.curtime + time_passed
		if (timehdr > self.maxtime):
			timehdr = self.maxtime
		return pack('<I', timehdr)

	
	
	def add(self, json, time_rcvd = None):
		if time_rcvd is None: time_rcvd = time()
		if self.version:
			raise ValueError("Template already populated (combining not supported)")
		
		self.diffbits = a2b_hex(json['bits'])[::-1]
		self.curtime = json['curtime']
		self.height = json['height']
		self.prevblk = a2b_hex(json['previousblockhash'])[::-1]
		self.sigoplimit = json.get('sigoplimit', self.sigoplimit)
		self.sizelimit = json.get('sizelimit', self.sizelimit)
		self.version = json['version']
		
		self.cbvalue = json.get('coinbasevalue', None)
		
		self.maxtime = json.get('maxtime', self.maxtime)
		self.maxtimeoff = json.get('maxtimeoff', self.maxtimeoff)
		self.mintime = json.get('mintime', self.mintime)
		self.mintimeoff = json.get('mintimeoff', self.mintimeoff)

		self._time_rcvd = time_rcvd
		self.cbtxn = Transaction(json['coinbasetxn'])
		self.target = a2b_hex(json['target'])
		self.noncerange = a2b_hex(json['noncerange'])
		
		
		self.txns = []
		self.txns_datasz = 0
		for t in json['transactions']:
			tobj = Transaction(t)
			self.txns.append(tobj)
			self.txns_datasz += len(tobj.data)
		
		self.mutations = set(json.get('mutable', ()))
		
		return True


	def submit(self, data, nonce):
		data = data[:76]
		data += pack('!I', nonce)
		data += self.varintEncode(1 + len(self.txns))
		data += self.cbtxn.data
		for i in range(len(self.txns)):
			data += self.txns[i].data
		return b2a_hex(data).decode('ascii')

	def varintEncode(self, n):
		if n < 0xfd:
			return pack('<B', n)
		# NOTE: Technically, there are more encodings for numbers bigger than
		# 16-bit, but transaction counts can't be that high with version 2 Bitcoin
		# blocks
		return b'\xfd' + pack('<H', n)