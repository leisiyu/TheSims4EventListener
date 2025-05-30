import sysimport socketfrom socket import _GLOBAL_DEFAULT_TIMEOUT__all__ = ['FTP', 'error_reply', 'error_temp', 'error_perm', 'error_proto', 'all_errors']MSG_OOB = 1FTP_PORT = 21MAXLINE = 8192
class Error(Exception):
    pass

class error_reply(Error):
    pass

class error_temp(Error):
    pass

class error_perm(Error):
    pass

class error_proto(Error):
    pass
all_errors = (Error, OSError, EOFError)CRLF = '\r\n'B_CRLF = b'\r\n'
class FTP:
    debugging = 0
    host = ''
    port = FTP_PORT
    maxline = MAXLINE
    sock = None
    file = None
    welcome = None
    passiveserver = 1
    encoding = 'latin-1'

    def __init__(self, host='', user='', passwd='', acct='', timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        self.source_address = source_address
        self.timeout = timeout
        if host:
            self.connect(host)
            if user:
                self.login(user, passwd, acct)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.sock is not None:
            try:
                self.quit()
            except (OSError, EOFError):
                pass
            finally:
                if self.sock is not None:
                    self.close()

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address
        self.sock = socket.create_connection((self.host, self.port), self.timeout, source_address=self.source_address)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        if self.debugging:
            print('*welcome*', self.sanitize(self.welcome))
        return self.welcome

    def set_debuglevel(self, level):
        self.debugging = level

    debug = set_debuglevel

    def set_pasv(self, val):
        self.passiveserver = val

    def sanitize(self, s):
        if s[:5] in frozenset({'PASS ', 'pass '}):
            i = len(s.rstrip('\r\n'))
            s = s[:5] + '*'*(i - 5) + s[i:]
        return repr(s)

    def putline(self, line):
        if '\r' in line or '\n' in line:
            raise ValueError('an illegal newline character should not be contained')
        line = line + CRLF
        if self.debugging > 1:
            print('*put*', self.sanitize(line))
        self.sock.sendall(line.encode(self.encoding))

    def putcmd(self, line):
        if self.debugging:
            print('*cmd*', self.sanitize(line))
        self.putline(line)

    def getline(self):
        line = self.file.readline(self.maxline + 1)
        if len(line) > self.maxline:
            raise Error('got more than %d bytes' % self.maxline)
        if self.debugging > 1:
            print('*get*', self.sanitize(line))
        if not line:
            raise EOFError
        if line[-2:] == CRLF:
            line = line[:-2]
        elif line[-1:] in CRLF:
            line = line[:-1]
        return line

    def getmultiline(self):
        line = self.getline()
        if line[3:4] == '-':
            code = line[:3]
            while True:
                nextline = self.getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and nextline[3:4] != '-':
                    break
        return line

    def getresp(self):
        resp = self.getmultiline()
        if self.debugging:
            print('*resp*', self.sanitize(resp))
        self.lastresp = resp[:3]
        c = resp[:1]
        if c in frozenset({'2', '3', '1'}):
            return resp
        if c == '4':
            raise error_temp(resp)
        if c == '5':
            raise error_perm(resp)
        raise error_proto(resp)

    def voidresp(self):
        resp = self.getresp()
        if resp[:1] != '2':
            raise error_reply(resp)
        return resp

    def abort(self):
        line = b'ABOR' + B_CRLF
        if self.debugging > 1:
            print('*put urgent*', self.sanitize(line))
        self.sock.sendall(line, MSG_OOB)
        resp = self.getmultiline()
        if resp[:3] not in frozenset({'226', '225', '426'}):
            raise error_proto(resp)
        return resp

    def sendcmd(self, cmd):
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        self.putcmd(cmd)
        return self.voidresp()

    def sendport(self, host, port):
        hbytes = host.split('.')
        pbytes = [repr(port//256), repr(port % 256)]
        bytes = hbytes + pbytes
        cmd = 'PORT ' + ','.join(bytes)
        return self.voidcmd(cmd)

    def sendeprt(self, host, port):
        af = 0
        if self.af == socket.AF_INET:
            af = 1
        if self.af == socket.AF_INET6:
            af = 2
        if af == 0:
            raise error_proto('unsupported address family')
        fields = ['', repr(af), host, repr(port), '']
        cmd = 'EPRT ' + '|'.join(fields)
        return self.voidcmd(cmd)

    def makeport(self):
        err = None
        sock = None
        for res in socket.getaddrinfo(None, 0, self.af, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            (af, socktype, proto, canonname, sa) = res
            try:
                sock = socket.socket(af, socktype, proto)
                sock.bind(sa)
            except OSError as _:
                err = _
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if sock is None:
            if err is not None:
                raise err
            else:
                raise OSError('getaddrinfo returns an empty list')
        sock.listen(1)
        port = sock.getsockname()[1]
        host = self.sock.getsockname()[0]
        if self.af == socket.AF_INET:
            resp = self.sendport(host, port)
        else:
            resp = self.sendeprt(host, port)
        if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(self.timeout)
        return sock

    def makepasv(self):
        if self.af == socket.AF_INET:
            (host, port) = parse227(self.sendcmd('PASV'))
        else:
            (host, port) = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        return (host, port)

    def ntransfercmd(self, cmd, rest=None):
        size = None
        if self.passiveserver:
            (host, port) = self.makepasv()
            conn = socket.create_connection((host, port), self.timeout, source_address=self.source_address)
            try:
                if rest is not None:
                    self.sendcmd('REST %s' % rest)
                resp = self.sendcmd(cmd)
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
            except:
                conn.close()
                raise
        else:
            with self.makeport() as sock:
                if rest is not None:
                    self.sendcmd('REST %s' % rest)
                resp = self.sendcmd(cmd)
                if resp[0] == '2':
                    resp = self.getresp()
                if resp[0] != '1':
                    raise error_reply(resp)
                (conn, sockaddr) = sock.accept()
                if self.timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                    conn.settimeout(self.timeout)
        if resp[:3] == '150':
            size = parse150(resp)
        return (conn, size)

    def transfercmd(self, cmd, rest=None):
        return self.ntransfercmd(cmd, rest)[0]

    def login(self, user='', passwd='', acct=''):
        if not user:
            user = 'anonymous'
        if not passwd:
            passwd = ''
        if not acct:
            acct = ''
        if passwd in frozenset({'', '-'}):
            passwd = passwd + 'anonymous@'
        resp = self.sendcmd('USER ' + user)
        if user == 'anonymous' and resp[0] == '3':
            resp = self.sendcmd('PASS ' + passwd)
        if resp[0] == '3':
            resp = self.sendcmd('ACCT ' + acct)
        if resp[0] != '2':
            raise error_reply(resp)
        return resp

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd, rest) as conn:
            while True:
                data = conn.recv(blocksize)
                if not data:
                    break
                callback(data)
            if _SSLSocket is not None and isinstance(conn, _SSLSocket):
                conn.unwrap()
        return self.voidresp()

    def retrlines(self, cmd, callback=None):
        if callback is None:
            callback = print_line
        resp = self.sendcmd('TYPE A')
        with self.transfercmd(cmd) as conn, conn.makefile('r', encoding=self.encoding) as fp:
            while True:
                line = fp.readline(self.maxline + 1)
                if len(line) > self.maxline:
                    raise Error('got more than %d bytes' % self.maxline)
                if self.debugging > 2:
                    print('*retr*', repr(line))
                if not line:
                    break
                if line[-2:] == CRLF:
                    line = line[:-2]
                elif line[-1:] == '\n':
                    line = line[:-1]
                callback(line)
            if _SSLSocket is not None and isinstance(conn, _SSLSocket):
                conn.unwrap()
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        self.voidcmd('TYPE I')
        with self.transfercmd(cmd, rest) as conn:
            while True:
                buf = fp.read(blocksize)
                if not buf:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
            if _SSLSocket is not None and isinstance(conn, _SSLSocket):
                conn.unwrap()
        return self.voidresp()

    def storlines(self, cmd, fp, callback=None):
        self.voidcmd('TYPE A')
        with self.transfercmd(cmd) as conn:
            while True:
                buf = fp.readline(self.maxline + 1)
                if len(buf) > self.maxline:
                    raise Error('got more than %d bytes' % self.maxline)
                if not buf:
                    break
                if buf[-2:] != B_CRLF:
                    if buf[-1] in B_CRLF:
                        buf = buf[:-1]
                    buf = buf + B_CRLF
                conn.sendall(buf)
                if callback:
                    callback(buf)
            if _SSLSocket is not None and isinstance(conn, _SSLSocket):
                conn.unwrap()
        return self.voidresp()

    def acct(self, password):
        cmd = 'ACCT ' + password
        return self.voidcmd(cmd)

    def nlst(self, *args):
        cmd = 'NLST'
        for arg in args:
            cmd = cmd + (' ' + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def dir(self, *args):
        cmd = 'LIST'
        func = None
        if type(args[-1]) != type(''):
            args = args[:-1]
            func = args[-1]
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.retrlines(cmd, func)

    def mlsd(self, path='', facts=[]):
        if facts:
            self.sendcmd('OPTS MLST ' + ';'.join(facts) + ';')
        if path:
            cmd = 'MLSD %s' % path
        else:
            cmd = 'MLSD'
        lines = []
        self.retrlines(cmd, lines.append)
        for line in lines:
            (facts_found, _, name) = line.rstrip(CRLF).partition(' ')
            entry = {}
            for fact in facts_found[:-1].split(';'):
                (key, _, value) = fact.partition('=')
                entry[key.lower()] = value
            yield (name, entry)

    def rename(self, fromname, toname):
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise error_reply(resp)
        return self.voidcmd('RNTO ' + toname)

    def delete(self, filename):
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in frozenset({'200', '250'}):
            return resp
        raise error_reply(resp)

    def cwd(self, dirname):
        if dirname == '..':
            try:
                return self.voidcmd('CDUP')
            except error_perm as msg:
                if msg.args[0][:3] != '500':
                    raise
        elif dirname == '':
            dirname = '.'
        cmd = 'CWD ' + dirname
        return self.voidcmd(cmd)

    def size(self, filename):
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            return int(s)

    def mkd(self, dirname):
        resp = self.voidcmd('MKD ' + dirname)
        if not resp.startswith('257'):
            return ''
        return parse257(resp)

    def rmd(self, dirname):
        return self.voidcmd('RMD ' + dirname)

    def pwd(self):
        resp = self.voidcmd('PWD')
        if not resp.startswith('257'):
            return ''
        return parse257(resp)

    def quit(self):
        resp = self.voidcmd('QUIT')
        self.close()
        return resp

    def close(self):
        try:
            file = self.file
            self.file = None
            if file is not None:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock is not None:
                sock.close()
try:
    import ssl
except ImportError:
    _SSLSocket = None_SSLSocket = ssl.SSLSocket
class FTP_TLS(FTP):
    ssl_version = ssl.PROTOCOL_TLS_CLIENT

    def __init__(self, host='', user='', passwd='', acct='', keyfile=None, certfile=None, context=None, timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        if context is not None and keyfile is not None:
            raise ValueError('context and keyfile arguments are mutually exclusive')
        if context is not None and certfile is not None:
            raise ValueError('context and certfile arguments are mutually exclusive')
        if keyfile is not None or certfile is not None:
            import warnings
            warnings.warn('keyfile and certfile are deprecated, use acustom context instead', DeprecationWarning, 2)
        self.keyfile = keyfile
        self.certfile = certfile
        if context is None:
            context = ssl._create_stdlib_context(self.ssl_version, certfile=certfile, keyfile=keyfile)
        self.context = context
        self._prot_p = False
        FTP.__init__(self, host, user, passwd, acct, timeout, source_address)

    def login(self, user='', passwd='', acct='', secure=True):
        if secure and not isinstance(self.sock, ssl.SSLSocket):
            self.auth()
        return FTP.login(self, user, passwd, acct)

    def auth(self):
        if isinstance(self.sock, ssl.SSLSocket):
            raise ValueError('Already using TLS')
        if self.ssl_version >= ssl.PROTOCOL_TLS:
            resp = self.voidcmd('AUTH TLS')
        else:
            resp = self.voidcmd('AUTH SSL')
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile(mode='r', encoding=self.encoding)
        return resp

    def ccc(self):
        if not isinstance(self.sock, ssl.SSLSocket):
            raise ValueError('not using TLS')
        resp = self.voidcmd('CCC')
        self.sock = self.sock.unwrap()
        return resp

    def prot_p(self):
        self.voidcmd('PBSZ 0')
        resp = self.voidcmd('PROT P')
        self._prot_p = True
        return resp

    def prot_c(self):
        resp = self.voidcmd('PROT C')
        self._prot_p = False
        return resp

    def ntransfercmd(self, cmd, rest=None):
        (conn, size) = FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host)
        return (conn, size)

    def abort(self):
        line = b'ABOR' + B_CRLF
        self.sock.sendall(line)
        resp = self.getmultiline()
        if resp[:3] not in frozenset({'226', '225', '426'}):
            raise error_proto(resp)
        return resp
__all__.append('FTP_TLS')all_errors = (Error, OSError, EOFError, ssl.SSLError)_150_re = None
def parse150(resp):
    global _150_re
    if resp[:3] != '150':
        raise error_reply(resp)
    if _150_re is None:
        import re
        _150_re = re.compile('150 .* \\((\\d+) bytes\\)', re.IGNORECASE | re.ASCII)
    m = _150_re.match(resp)
    if not m:
        return
    return int(m.group(1))
_227_re = None
def parse227(resp):
    global _227_re
    if resp[:3] != '227':
        raise error_reply(resp)
    if _227_re is None:
        import re
        _227_re = re.compile('(\\d+),(\\d+),(\\d+),(\\d+),(\\d+),(\\d+)', re.ASCII)
    m = _227_re.search(resp)
    if not m:
        raise error_proto(resp)
    numbers = m.groups()
    host = '.'.join(numbers[:4])
    port = (int(numbers[4]) << 8) + int(numbers[5])
    return (host, port)

def parse229(resp, peer):
    if resp[:3] != '229':
        raise error_reply(resp)
    left = resp.find('(')
    if left < 0:
        raise error_proto(resp)
    right = resp.find(')', left + 1)
    if right < 0:
        raise error_proto(resp)
    if resp[left + 1] != resp[right - 1]:
        raise error_proto(resp)
    parts = resp[left + 1:right].split(resp[left + 1])
    if len(parts) != 5:
        raise error_proto(resp)
    host = peer[0]
    port = int(parts[3])
    return (host, port)

def parse257(resp):
    if resp[:3] != '257':
        raise error_reply(resp)
    if resp[3:5] != ' "':
        return ''
    dirname = ''
    i = 5
    n = len(resp)
    while i < n:
        c = resp[i]
        i = i + 1
        if c == '"':
            if i >= n or resp[i] != '"':
                break
            i = i + 1
        dirname = dirname + c
    return dirname

def print_line(line):
    print(line)

def ftpcp(source, sourcename, target, targetname='', type='I'):
    if not targetname:
        targetname = sourcename
    type = 'TYPE ' + type
    source.voidcmd(type)
    target.voidcmd(type)
    (sourcehost, sourceport) = parse227(source.sendcmd('PASV'))
    target.sendport(sourcehost, sourceport)
    treply = target.sendcmd('STOR ' + targetname)
    if treply[:3] not in frozenset({'125', '150'}):
        raise error_proto
    sreply = source.sendcmd('RETR ' + sourcename)
    if sreply[:3] not in frozenset({'125', '150'}):
        raise error_proto
    source.voidresp()
    target.voidresp()

def test():
    if len(sys.argv) < 2:
        print(test.__doc__)
        sys.exit(0)
    import netrc
    debugging = 0
    rcfile = None
    while sys.argv[1] == '-d':
        debugging = debugging + 1
        del sys.argv[1]
    if sys.argv[1][:2] == '-r':
        rcfile = sys.argv[1][2:]
        del sys.argv[1]
    host = sys.argv[1]
    ftp = FTP(host)
    ftp.set_debuglevel(debugging)
    userid = passwd = acct = ''
    try:
        netrcobj = netrc.netrc(rcfile)
    except OSError:
        if rcfile is not None:
            sys.stderr.write('Could not open account file -- using anonymous login.')
    try:
        (userid, acct, passwd) = netrcobj.authenticators(host)
    except KeyError:
        sys.stderr.write('No account -- using anonymous login.')
    ftp.login(userid, passwd, acct)
    for file in sys.argv[2:]:
        if file[:2] == '-l':
            ftp.dir(file[2:])
        elif file[:2] == '-d':
            cmd = 'CWD'
            if file[2:]:
                cmd = cmd + ' ' + file[2:]
            resp = ftp.sendcmd(cmd)
        elif file == '-p':
            ftp.set_pasv(not ftp.passiveserver)
        else:
            ftp.retrbinary('RETR ' + file, sys.stdout.write, 1024)
    ftp.quit()
if __name__ == '__main__':
    test()