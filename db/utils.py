import hashlib

def id_to_ref_code(user_id: int) -> str:
    """Генерирует код из ID"""
    hash_obj = hashlib.md5(str(user_id).encode())
    hex_digest = hash_obj.hexdigest()
    return hex_digest[:8].upper() 