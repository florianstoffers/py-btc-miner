from base58 import b58decode_check

def get_le_hex(value: int, width: int) -> str:
    return value.to_bytes(width, byteorder='little').hex()


def get_le_var_hex(value: int) -> str:
    if value < 0xfd:
        return get_le_hex(value, 1)
    if value <= 0xffff:
        return "fd" + get_le_hex(value, 2)
    if value <= 0xffffffff:
        return "fe" + get_le_hex(value, 4)
    return "ff" + get_le_hex(value, 8)


def encode_coinbase_height(height: int) -> str:
    """
    https://github.com/bitcoin/bips/blob/master/bip-0034.mediawiki
    """
    width = (height.bit_length() + 7) // 8
    return bytes([width]).hex() + get_le_hex(height, width)


def create_coinbase(
    coinbase_value: int, 
    coinbase_text: str, 
    block_height: int,
    wallet_address: str
) -> str:
    coinbase_script = encode_coinbase_height(block_height) + coinbase_text
    pubkey_script = "76a914" + b58decode_check(wallet_address)[1:].hex() + "88ac"
    return (
        "0100000001" + "0" * 64 + "ffffffff" 
        + get_le_var_hex(len(coinbase_script) // 2) 
        + coinbase_script + "ffffffff01" 
        + get_le_hex(coinbase_value, 8)
        + get_le_var_hex(len(pubkey_script) // 2)
        + pubkey_script
        + "00000000"
    )


