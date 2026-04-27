import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
buf = __import__("io").BytesIO()
plt.gcf().savefig(buf, format="png")
print("OK", len(buf.getvalue()))
