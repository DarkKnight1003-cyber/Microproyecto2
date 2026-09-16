import io
import flask
import torch
from torchvision import models
from PIL import Image

app = flask.Flask(__name__)

weights = models.ResNet18_Weights.DEFAULT
net = models.resnet18(weights=weights)
net.eval()

transform_fn = weights.transforms()
class_names = weights.meta["categories"]

@app.route("/predict", methods=["POST"])
def predict():
    if flask.request.method == "POST":
        if flask.request.files.get("img"):
            img = Image.open(io.BytesIO(flask.request.files["img"].read())).convert("RGB")
            img_t = transform_fn(img)
            batch_t = img_t.unsqueeze(0)
            with torch.no_grad():
                pred = net(batch_t)
            probs = torch.nn.functional.softmax(pred[0], dim=0)
            ind = torch.argmax(probs).item()
            prediction = ('The input picture is classified as [%s], with probability %.3f.' %
                         (class_names[ind], probs[ind].item()))
    return prediction

if __name__ == '__main__':
    app.run(host='0.0.0.0')