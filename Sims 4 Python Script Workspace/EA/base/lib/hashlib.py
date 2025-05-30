'''hashlib module - A common interface to many hash functions.

new(name, data=b'', **kwargs) - returns a new hash object implementing the
                                given hash function; initializing the hash
                                using the given binary data.

Named constructor functions are also available, these are faster
than using new(name):

md5(), sha1(), sha224(), sha256(), sha384(), sha512(), blake2b(), blake2s(),
sha3_224, sha3_256, sha3_384, sha3_512, shake_128, and shake_256.

More algorithms may be available on your platform but the above are guaranteed
to exist.  See the algorithms_guaranteed and algorithms_available attributes
to find out what algorithm names can be passed to new().

NOTE: If you want the adler32 or crc32 hash functions they are available in
the zlib module.

Choose your hash function wisely.  Some have known collision weaknesses.
sha384 and sha512 will be slow on 32 bit platforms.

Hash objects have these methods:
 - update(arg): Update the hash object with the bytes in arg. Repeated calls
                are equivalent to a single call with the concatenation of all
                the arguments.
 - digest():    Return the digest of the bytes passed to the update() method
                so far.
 - hexdigest(): Like digest() except the digest is returned as a unicode
                object of double length, containing only hexadecimal digits.
 - copy():      Return a copy (clone) of the hash object. This can be used to
                efficiently compute the digests of strings that share a common
                initial substring.

For example, to obtain the digest of the string 'Nobody inspects the
spammish repetition':

    >>> import hashlib
    >>> m = hashlib.md5()
    >>> m.update(b"Nobody inspects")
    >>> m.update(b" the spammish repetition")
    >>> m.digest()
    b'\\xbbd\\x9c\\x83\\xdd\\x1e\\xa5\\xc9\\xd9\\xde\\xc9\\xa1\\x8d\\xf0\\xff\\xe9'

More condensed:

    >>> hashlib.sha224(b"Nobody inspects the spammish repetition").hexdigest()
    'a4337bc45a8fc544c03f52dc550cd6e1e87021bc896588bd79e901e2'

'''__always_supported = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'blake2b', 'blake2s', 'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512', 'shake_128', 'shake_256')algorithms_guaranteed = set(__always_supported)algorithms_available = set(__always_supported)__all__ = __always_supported + ('new', 'algorithms_guaranteed', 'algorithms_available', 'pbkdf2_hmac')__builtin_constructor_cache = {}
def __get_builtin_constructor(name):
    cache = __builtin_constructor_cache
    constructor = cache.get(name)
    if constructor is not None:
        return constructor
    try:
        if name in ('SHA1', 'sha1'):
            import _sha1
            cache['SHA1'] = cache['sha1'] = _sha1.sha1
        elif name in ('MD5', 'md5'):
            import _md5
            cache['MD5'] = cache['md5'] = _md5.md5
        elif name in ('SHA256', 'sha256', 'SHA224', 'sha224'):
            import _sha256
            cache['SHA224'] = cache['sha224'] = _sha256.sha224
            cache['SHA256'] = cache['sha256'] = _sha256.sha256
        elif name in ('SHA512', 'sha512', 'SHA384', 'sha384'):
            import _sha512
            cache['SHA384'] = cache['sha384'] = _sha512.sha384
            cache['SHA512'] = cache['sha512'] = _sha512.sha512
        elif name in ('blake2b', 'blake2s'):
            import _blake2
            cache['blake2b'] = _blake2.blake2b
            cache['blake2s'] = _blake2.blake2s
        elif name in frozenset({'sha3_384', 'shake_256', 'sha3_224', 'sha3_256', 'sha3_512', 'shake_128'}):
            import _sha3
            cache['sha3_224'] = _sha3.sha3_224
            cache['sha3_256'] = _sha3.sha3_256
            cache['sha3_384'] = _sha3.sha3_384
            cache['sha3_512'] = _sha3.sha3_512
            cache['shake_128'] = _sha3.shake_128
            cache['shake_256'] = _sha3.shake_256
    except ImportError:
        pass
    constructor = cache.get(name)
    if constructor is not None:
        return constructor
    raise ValueError('unsupported hash type ' + name)

def __get_openssl_constructor(name):
    if name in frozenset({'blake2b', 'blake2s'}):
        return __get_builtin_constructor(name)
    try:
        f = getattr(_hashlib, 'openssl_' + name)
        f()
        return f
    except (AttributeError, ValueError):
        return __get_builtin_constructor(name)

def __py_new(name, data=b'', **kwargs):
    return __get_builtin_constructor(name)(data, **kwargs)

def __hash_new(name, data=b'', **kwargs):
    if name in frozenset({'blake2b', 'blake2s'}):
        return __get_builtin_constructor(name)(data, **kwargs)
    try:
        return _hashlib.new(name, data)
    except ValueError:
        return __get_builtin_constructor(name)(data)
try:
    import _hashlib
    new = __hash_new
    __get_hash = __get_openssl_constructor
    algorithms_available = algorithms_available.union(_hashlib.openssl_md_meth_names)
except ImportError:
    new = __py_new
    __get_hash = __get_builtin_constructortry:
    from _hashlib import pbkdf2_hmac
except ImportError:
    _trans_5C = bytes(x ^ 92 for x in range(256))
    _trans_36 = bytes(x ^ 54 for x in range(256))

    def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        if not isinstance(hash_name, str):
            raise TypeError(hash_name)
        if not isinstance(password, (bytes, bytearray)):
            password = bytes(memoryview(password))
        if not isinstance(salt, (bytes, bytearray)):
            salt = bytes(memoryview(salt))
        inner = new(hash_name)
        outer = new(hash_name)
        blocksize = getattr(inner, 'block_size', 64)
        if len(password) > blocksize:
            password = new(hash_name, password).digest()
        password = password + b'\x00'*(blocksize - len(password))
        inner.update(password.translate(_trans_36))
        outer.update(password.translate(_trans_5C))

        def prf(msg, inner=inner, outer=outer):
            icpy = inner.copy()
            ocpy = outer.copy()
            icpy.update(msg)
            ocpy.update(icpy.digest())
            return ocpy.digest()

        if iterations < 1:
            raise ValueError(iterations)
        if dklen is None:
            dklen = outer.digest_size
        if dklen < 1:
            raise ValueError(dklen)
        dkey = b''
        loop = 1
        from_bytes = int.from_bytes
        while len(dkey) < dklen:
            prev = prf(salt + loop.to_bytes(4, 'big'))
            rkey = int.from_bytes(prev, 'big')
            for i in range(iterations - 1):
                prev = prf(prev)
                rkey ^= from_bytes(prev, 'big')
            loop += 1
            dkey += rkey.to_bytes(inner.digest_size, 'big')
        return dkey[:dklen]
try:
    from _hashlib import scrypt
except ImportError:
    passfor __func_name in __always_supported:
    try:
        globals()[__func_name] = __get_hash(__func_name)
    except ValueError:
        import logging
        logging.exception('code for hash %s was not found.', __func_name)del __always_supporteddel __func_namedel __get_hashdel __py_newdel __hash_newdel __get_openssl_constructor