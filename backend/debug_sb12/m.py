import json as _json, sys as _sys
_STAGED = _json.loads('{}')

def out(_obj):
    _sys.stdout.write('<<ARTIFACT::start>>')
    _sys.stdout.write(_json.dumps(_obj, default=str))
    _sys.stdout.write('<<ARTIFACT::end>>')
    _sys.stdout.write("\n")

def _apply_app_mpl_style():
    import matplotlib as _mpl
    _mpl.use("Agg")
    from cycler import cycler as _cycler

def out_image(fig=None, *, title=None, caption=None):
    import io as _io, base64 as _b64
    import matplotlib.pyplot as _plt
    if "_app_mpl_style_applied" not in globals():
        _apply_app_mpl_style()
        globals()["_app_mpl_style_applied"] = True
    f = fig if fig is not None else _plt.gcf()

print("hi")
