"""
Maritime AI Inference Pipeline
-----------------------------
Cascade system for vessel detection, classification, and day shape recognition.
Developed for MarineNav-MVP.
"""

import os
import json
import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from ultralytics import YOLO
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any


class MaritimeDetector:
    """
    Main detector class that performs:
    1. Vessel detection (YOLO11n)
    2. Sailboat vs Power-driven classification (EfficientNet-B0)
    3. Day shapes detection and priority logic (YOLO11n Custom)
    """

    def __init__(self, binary_model_path: str, shapes_model_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🚀 Initializing Maritime AI Core on {self.device}")

        # 1. Base Vessel Detector (COCO class 8: boat)
        self.base_yolo = YOLO("yolo11n.pt")

        # 2. Day Shapes Detector
        self.shapes_yolo = YOLO(shapes_model_path)
        self.shape_classes = {
            0: "ball", 
            1: "diamond", 
            2: "cylinder", 
            3: "cone_up", 
            4: "cone_down"
        }

        # 3. Binary Classifier (Sailing vs Power-driven)
        self.binary_model = self._load_binary_classifier(binary_model_path)
        self.binary_classes = {0: "Power-driven", 1: "Sailing"}
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        # 4. COLREG Priority Rules
        self.priority_rules = {
            ("ball", "ball"): "NUC",
            ("ball", "diamond", "ball"): "RAM",
            ("cylinder",): "CBD",
            ("cone_up", "cone_down"): "Fishing",
            ("cone_down",): "Power-driven"
        }

        # Thresholds
        self.min_vessel_conf = 0.25
        self.min_shape_conf = 0.45

    def _load_binary_classifier(self, model_path: str) -> nn.Module:
        """Initializes and loads the EfficientNet-B0 model."""
        model = models.efficientnet_b0(weights=None)
        num_ftrs = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_ftrs, 2)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model weight file not found: {model_path}")
            
        model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        model.to(self.device)
        model.eval()
        return model

    def _analyze_shapes(self, crop_img: np.ndarray) -> Tuple[Optional[str], float]:
        """Detects shapes on mast and returns COLREG status."""
        # Use agnostic_nms to prevent overlapping boxes of different classes
        results = self.shapes_yolo(crop_img, verbose=False, imgsz=1024, conf=0.50, agnostic_nms=True)
        
        detected = []
        if results and results[0].boxes:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                y_coord = float(box.xywh[0][1].item())
                detected.append({"class": self.shape_classes.get(cls_id), "y": y_coord, "conf": conf})

        if not detected:
            return None, 0.0

        # Sort shapes vertically (top to bottom)
        sorted_shapes = sorted(detected, key=lambda s: s['y'])
        sequence = tuple(s['class'] for s in sorted_shapes)
        avg_conf = sum(s['conf'] for s in sorted_shapes) / len(sorted_shapes)

        # Map "Aground" (3 balls) to "NUC" to respect the 6 allowed classes
        priority_rules = {
            ("ball", "ball"): "NUC",
            ("ball", "ball", "ball"): "NUC",
            ("ball", "diamond", "ball"): "RAM",
            ("cylinder",): "CBD",
            ("cone_up", "cone_down"): "Fishing",
            ("cone_down",): "Power-driven"
        }

        # 1. Strict match
        if sequence in priority_rules:
            return priority_rules[sequence], avg_conf
        
        # 2. Heuristic fallback (Strict Priority Order to prevent false override)
        cls_list = [s['class'] for s in sorted_shapes]
        
        # Highest Priority: RAM (Requires at least 2 balls and 1 diamond)
        if cls_list.count("ball") >= 2 and "diamond" in cls_list:
            return "RAM", avg_conf
            
        # Priority: NUC (Requires at least 2 balls)
        if cls_list.count("ball") >= 2:
            return "NUC", avg_conf
            
        # Priority: Fishing (Requires both cones)
        if "cone_down" in cls_list and "cone_up" in cls_list:
            return "Fishing", avg_conf
            
        # Priority: CBD (Requires cylinder)
        if "cylinder" in cls_list:
            return "CBD", avg_conf
            
        # Priority: Motor-Sailing (Requires cone pointing down)
        if "cone_down" in cls_list:
            return "Power-driven", avg_conf
            
        return None, 0.0

    def _classify_vessel_type(self, crop_img: np.ndarray) -> Tuple[str, float]:
        """Performs binary classification on the vessel crop."""
        rgb_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.binary_model(input_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)
            conf, pred = torch.max(probs, 1)
            
        return self.binary_classes[pred.item()], conf.item()

    def process_image(self, image_path: str) -> str:
        """
        Processes an image and returns results in JSON format.
        """
        img = cv2.imread(image_path)
        if img is None:
            return json.dumps({"error": f"Failed to load image: {image_path}"})

        timestamp = datetime.now(timezone.utc).isoformat()
        detections = []

        # Step 1: Detect Vessels
        vessel_results = self.base_yolo(img, classes=[8], verbose=False, conf=self.min_vessel_conf)
        
        if not vessel_results or not vessel_results[0].boxes:
            return json.dumps([], indent=4)

        for i, box in enumerate(vessel_results[0].boxes):
            v_conf = float(box.conf[0].item())
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
            # Step 2: Dynamic Cropping (capturing the mast)
            h, w, _ = img.shape
            vh, vw = y2 - y1, x2 - x1
            
            # Significant top padding for day shapes
            p_top, p_bot, p_side = int(vh * 2.5), int(vh * 0.2), int(vw * 0.5)
            cy1, cy2 = max(0, y1 - p_top), min(h, y2 + p_bot)
            cx1, cx2 = max(0, x1 - p_side), min(w, x2 + p_side)
            
            crop = img[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            # Step 3: Classify & Analyze
            base_type, b_conf = self._classify_vessel_type(crop)
            priority_type, s_conf = self._analyze_shapes(crop)

            if priority_type:
                final_type, final_conf = priority_type, (v_conf + s_conf) / 2.0
            else:
                final_type, final_conf = base_type, (v_conf + b_conf) / 2.0

            detections.append({
                "target_id": i + 1,
                "type": final_type,
                "confidence": round(final_conf, 3),
                "timestamp": timestamp,
                "bbox": [x1, y1, x2, y2]
            })

        return json.dumps(detections, indent=4)


if __name__ == "__main__":
    # Example usage
    PIPELINE = MaritimeDetector("models/best_model.pth", "models/best.pt")
    # Add your test run here
