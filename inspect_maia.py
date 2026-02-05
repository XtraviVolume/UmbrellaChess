import maia2.model
import maia2.inference

print("Model attributes:")
try:
    model = maia2.model.from_pretrained(type="rapid", device="cpu")
    print(dir(model))
    print("Model type:", type(model))
except Exception as e:
    print(e)

