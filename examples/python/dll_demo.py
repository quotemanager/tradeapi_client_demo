"""Generic cdecl/UTF-8 DLL example; DLLs are not distributed in this repository."""
import ctypes
import json
import os
from pathlib import Path
import sys
from client import connection, dry_run, make_request


def main():
    product, profile, spec, body, execute = make_request(sys.argv[1:])
    if dry_run(spec, body, execute):
        return 0
    url, token = connection(profile)
    home = os.environ.get('TRADEAPI_' + product.upper() + '_HOME')
    if not home:
        raise ValueError('Set TRADEAPI_' + product.upper() + '_HOME')
    arch = 'x64' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'x86'
    dll = ctypes.CDLL(str(Path(home) / 'build' / arch / ('tradeapi_' + product + '.dll')))
    output_args = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
    dll.TradeApi_Initialize.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.TradeApi_Call.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, *output_args]
    dll.TradeApi_GetLastResponse.argtypes = output_args
    dll.TradeApi_GetLastHttpStatus.restype = ctypes.c_uint32
    if dll.TradeApi_Initialize(url.encode(), token.encode()):
        raise ValueError('DLL initialization failed')
    buffer, required = ctypes.create_string_buffer(65536), ctypes.c_uint32()
    raw = None if body is None else json.dumps(body, allow_nan=False).encode('utf-8')
    code = dll.TradeApi_Call(spec['method'].encode(), spec['path'].encode(), raw,
                            buffer, len(buffer), ctypes.byref(required))
    if code == 3:
        if not 0 < required.value <= 16 * 1024 * 1024 + 1:
            raise ValueError('Invalid DLL output size; nothing resent')
        buffer = ctypes.create_string_buffer(required.value)
        # SAME thread, copy only. Never repeat the original action to grow a buffer.
        code = dll.TradeApi_GetLastResponse(buffer, len(buffer), ctypes.byref(required))
    if code not in (0, 4):
        raise ValueError('DLL code=' + str(code) + '; outcome may be unknown; do not resubmit')
    status = dll.TradeApi_GetLastHttpStatus()
    response = json.loads(buffer.value)
    print('HTTP', status)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if status == 200 and response.get('ok') is not False else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(1)
