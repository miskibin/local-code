import matplotlib
matplotlib.use("Agg")
mod = __import__("matplotlib.pyplot", fromlist=["pyplot"])
mod.plot([1,2,3])
import io
buf = io.BytesIO()
mod.gcf().savefig(buf, format="png")
print("OK", len(buf.getvalue()))
