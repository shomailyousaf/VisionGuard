
from pathlib import Path
import random
import matplotlib.pyplot as plt
from PIL import Image

root = Path(__file__).resolve().parent.parent
ai_dir = root / "data" / "AiArtData" / "AiArtData"
real_dir = root / "data" / "RealArt" / "RealArt"
output_dir = root / "reports" / "screenshots"
output_dir.mkdir(parents=True, exist_ok=True)

random.seed(42)
ai_images = sorted([p for p in ai_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}])
real_images = sorted([p for p in real_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}])
sample_size = 5
ai_samples = random.sample(ai_images, min(sample_size, len(ai_images)))
real_samples = random.sample(real_images, min(sample_size, len(real_images)))

fig, axes = plt.subplots(2, sample_size, figsize=(15, 7))

for column, path in enumerate(ai_samples):
    with Image.open(path) as image:
        axes[0, column].imshow(image.convert("RGB"))
    axes[0, column].set_title("AI-generated")
    axes[0, column].axis("off")

for column, path in enumerate(real_samples):
    with Image.open(path) as image:
        axes[1, column].imshow(image.convert("RGB"))
    axes[1, column].set_title("Real")
    axes[1, column].axis("off")

fig.suptitle("Sample Images: AI-generated vs Real", fontsize=16)
plt.tight_layout()
output_path = output_dir / "visual_eda_samples.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")


print(f"AI-generated images available: {len(ai_images)}")
print(f"Real images available: {len(real_images)}")
print(f"Sample grid saved to: {output_path}")
