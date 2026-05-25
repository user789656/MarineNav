# ⚓ MarineNav CV-Core

Интеллектуальный модуль распознавания судов и навигационных знаков (МППСС-72).

## 📁 Структура репозитория
*   `main` (эта ветка): Содержит только обученные модели и пайплайн для инференса.
*   `data-and-prep`: Содержит скрипты генерации датасетов, отчеты об обучении и инструменты подготовки данных.

## 🚀 Быстрый старт (Inference)
```python
from inference_pipeline import MaritimeDetector

# Модели находятся в папке models/
detector = MaritimeDetector("models/best_model.pth", "models/best.pt")
results = detector.process_image("test_image.jpg")
print(results)
```

## 🛠 Установка
1. `pip install ultralytics torch torchvision opencv-python pillow`
2. Склонируйте репозиторий и используйте `inference_pipeline.py`.

---
Разработано для MarineNav-MVP.
