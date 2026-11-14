
import cv2
import glob
import os

from api import severity

os.makedirs("out", exist_ok=True)

image_paths = glob.glob("samples/*.jpg")
image_paths += glob.glob("samples/*.jpeg")
image_paths += glob.glob("samples/*.JPG")

if not image_paths:
    print("No JPG images found inside samples!")
    
for p in sorted(set(image_paths)):
    img = cv2.imread(p)

    if img is None:
        print("Could not read:", p)
        continue

    r = severity.estimate(img)

    print(
        os.path.basename(p),
        "Severity:", r["percent"], "%",
        "Level:", r["level"],
        "Leaf detected:", r["leaf_ok"]
    )

    output_path = os.path.join(
        "out", os.path.basename(p)
    )

    cv2.imwrite(output_path, r["overlay_bgr"])

print("\nTesting completed! Check the out folder.")
