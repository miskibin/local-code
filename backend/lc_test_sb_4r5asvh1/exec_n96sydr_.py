import json as _json, sys as _sys
_STAGED = _json.loads('{}')

# Pre-import the scientific stack at the TOP LEVEL so the wrapper's
# find_imports picks them up and install_imports() resolves them via
# micropip ONCE per session. Without these imports, user code like
# `import matplotlib.pyplot as plt` would surface as
# `matplotlib.pyplot` to install_imports — which then tries to fetch
# a non-existent `matplotlib-pyplot` package from PyPI and fails.
# Top-level `import matplotlib` instead loads the real package; the
# submodule import in user code becomes a no-op resolution against
# already-loaded matplotlib.
try:
    import matplotlib as _bootstrap_mpl  # noqa: F401
except ImportError:
    pass
try:
    import numpy as _bootstrap_np  # noqa: F401
except ImportError:
    pass
try:
    import pandas as _bootstrap_pd  # noqa: F401
except ImportError:
    pass

def out(_obj):
    _sys.stdout.write('<<ARTIFACT::start>>')
    _sys.stdout.write(_json.dumps(_obj, default=str))
    _sys.stdout.write('<<ARTIFACT::end>>')
    _sys.stdout.write("\n")

def _apply_app_mpl_style():
    # Imports go through importlib.import_module rather than top-level
    # `import matplotlib` so that the sandbox wrapper's `find_imports` AST
    # scan doesn't try to micropip-install matplotlib on every call.
    # matplotlib loads lazily when the agent first calls out_image().
    import importlib as _imp
    _mpl = _imp.import_module("matplotlib")
    _mpl.use("Agg")
    _cycler = _imp.import_module("cycler").cycler
    _ink_text = "#1f1f1f"
    _ink_spine = "#6b6b6b"
    _grid = "#c8c8c8"
    _mpl.rcParams.update({
        "figure.facecolor": "none",
        "figure.edgecolor": "none",
        "figure.dpi": 120,
        "axes.facecolor": "none",
        "axes.edgecolor": _ink_spine,
        "axes.labelcolor": _ink_text,
        "axes.titlecolor": _ink_text,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "medium",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.prop_cycle": _cycler(color=[
            "#3b82f6", "#10b981", "#f59e0b",
            "#ec4899", "#8b5cf6", "#06b6d4",
        ]),
        "grid.color": _grid,
        "grid.alpha": 0.28,
        "grid.linestyle": ":",
        "text.color": _ink_text,
        "xtick.color": _ink_text,
        "ytick.color": _ink_text,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.size": 11,
        "font.weight": "medium",
        "legend.frameon": False,
        "legend.fontsize": 10,
        "legend.labelcolor": _ink_text,
        "savefig.facecolor": "none",
        "savefig.edgecolor": "none",
        "savefig.transparent": True,
    })

def out_image(fig=None, *, title=None, caption=None):
    import io as _io, base64 as _b64, importlib as _imp
    if "_app_mpl_style_applied" not in globals():
        _apply_app_mpl_style()
        globals()["_app_mpl_style_applied"] = True
    _plt = _imp.import_module("matplotlib.pyplot")
    f = fig if fig is not None else _plt.gcf()
    buf = _io.BytesIO()
    f.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    out({
        "_image_png_b64": _b64.b64encode(buf.getvalue()).decode("ascii"),
        "title": title,
        "caption": caption,
    })

def read_artifact(_id):
    '''Load a prior artifact by id (literal in script source). Tables ->
    pandas DataFrame; images -> raw PNG bytes; text -> str.'''
    _meta = _STAGED.get(_id)
    if _meta is None:
        raise LookupError(
            f"artifact {_id!r} not staged; the runner only stages ids "
            f"that appear literally in the script source."
        )
    _kind = _meta.get("kind")
    _payload = _meta.get("payload") or {}
    if _kind == "table":
        try:
            import importlib as _imp
            _pd = _imp.import_module("pandas")
            return _pd.DataFrame(_payload.get("rows", []))
        except ImportError:
            return _payload.get("rows", [])
    if _kind == "image":
        import base64 as _b64
        return _b64.b64decode(_payload.get("data_b64", ""))
    if _kind == "text":
        return _payload.get("text", "")
    return _payload
open(r'C:/Windows/System32/drivers/etc/hosts').read()