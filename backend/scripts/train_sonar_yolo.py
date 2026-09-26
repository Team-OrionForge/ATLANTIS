"""YOLOv8-Seg training script for Project Atlantis Side-Scan Sonar (SSS) target segmentation.

Finetunes lightweight YOLOv8n-Seg model on procedurally generated ocean sonar target dataset.
Exports trained weights to backend root directory as 'yolov8n-seg.pt' for real deep learning inference.
"""

import os
from pathlib import Path
from ultralytics import YOLO
from scripts.generate_yolo_dataset import generate_dataset


def train_model(epochs: int = 15, batch_size: int = 16, imgsz: int = 640):
    """Generate dataset and train YOLOv8n-Seg model."""
    backend_dir = Path(__file__).resolve().parent.parent
    dataset_dir = backend_dir / "data" / "dataset"
    yaml_path = dataset_dir / "dataset.yaml"

    if not yaml_path.exists():
        print("Dataset not found. Generating synthetic dataset now...")
        generate_dataset(output_dir=str(dataset_dir), num_train=250, num_val=50)

    print("\n=======================================================")
    print("Starting YOLOv8n-Seg Training on Side-Scan Sonar Dataset")
    print("=======================================================\n")

    # Load pre-trained nano segmentation model baseline
    model = YOLO("yolov8n-seg.pt")

    # Train model
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        project=str(backend_dir / "runs"),
        name="sonar_yolo_seg",
        exist_ok=True,
        verbose=True,
    )

    # Copy best trained weights to backend root
    best_weights = backend_dir / "runs" / "sonar_yolo_seg" / "weights" / "best.pt"
    target_weights = backend_dir / "yolov8n-seg.pt"

    if best_weights.exists():
        import shutil
        shutil.copy(best_weights, target_weights)
        print(f"\n[OK] Successfully trained model and exported weights to: {target_weights}")
        print("[OK] Backend detector will now use real YOLOv8 neural network inference!")
    else:
        print("\n[WARNING] Training complete, but best.pt was not found at expected location.")


if __name__ == "__main__":
    train_model(epochs=15)
