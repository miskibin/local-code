import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
import io
buf = io.BytesIO()
plt.gcf().savefig(buf, format="png")
print("OK", len(buf.getvalue()))
