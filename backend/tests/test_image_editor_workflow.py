"""
Image Generation & Image Editor Real Workflow Integration Test
Uploads a real PNG image, executes transform_image and generate_image, and verifies output.
"""
from io import BytesIO
from PIL import Image as PILImage
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def create_test_png_bytes(width=256, height=256, color=(120, 90, 220, 255)) -> bytes:
    img = PILImage.new("RGBA", (width, height), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_editor_full_workflow():
    # 1. Login
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload actual PNG image to /api/images/edit
    real_png = create_test_png_bytes(width=300, height=200) # non-square input to verify square padding!
    
    files = {
        "image": ("my_artwork.png", BytesIO(real_png), "image/png"),
    }
    data = {
        "prompt": "Add soft glowing neon rim light and cybernetic aesthetics",
        "style": "Cinematic",
        "ratio": "1:1",
    }
    res = client.post("/api/images/edit", data=data, files=files, headers=headers)
    assert res.status_code == 200, f"Image edit failed with status {res.status_code}: {res.text}"
    
    body = res.json()
    assert body["success"] is True
    assert "filename" in body
    assert "image" in body
    assert "provider" in body
    print(f"Image Edit Success! Provider used: {body['provider']}, File: {body['filename']}")

    # 3. Verify static serving of the generated image
    img_res = client.get(body["image"])
    assert img_res.status_code == 200
    assert len(img_res.content) > 100
    assert img_res.headers["content-type"].startswith("image/")


def test_image_generation_full_workflow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "prompt": "Futuristic crystalline metropolis at golden hour",
        "style": "Photorealistic",
        "ratio": "1:1",
        "negative_prompt": "blurry, low quality",
    }
    res = client.post("/api/images/generate", data=data, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "image" in body

    img_res = client.get(body["image"])
    assert img_res.status_code == 200

