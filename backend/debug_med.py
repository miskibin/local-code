import json as _json, sys as _sys
_STAGED = _json.loads('{}')

def out(_obj):
    _sys.stdout.write('<<ARTIFACT::start>>')
    _sys.stdout.write(_json.dumps(_obj, default=str))
    _sys.stdout.write('<<ARTIFACT::end>>')
    _sys.stdout.write("\n")

print("hi")
