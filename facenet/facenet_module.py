"""
Модуль facenet_module.py

Обертка для FaceNet с использованием facenet-pytorch для детекции и извлечения эмбеддингов лиц.
"""
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import transforms

class FaceNet:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.mtcnn = MTCNN(keep_all=True, thresholds=[0.90, 0.90, 0.90], device=self.device)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def normalize_image(self, face_img):
        if face_img.mode != 'RGB':
            face_img = face_img.convert('RGB')
        face_tensor = self.transform(face_img)
        face_tensor = face_tensor.unsqueeze(0)
        return face_tensor

    def normalize_embedding(self, embedding):
        norm = torch.linalg.norm(embedding, dim=1, keepdim=True)
        normalized_embedding = embedding / norm
        return normalized_embedding

    def euclidean_distance(self, emb1, emb2):
        return torch.norm(emb1 - emb2).item()
    
    def detect_faces(self, image):
        image = image.convert('RGB')
        boxes, _ = self.mtcnn.detect(image)
        if boxes is not None:
            return boxes.tolist()
        return []
    
    def extract_embeddings(self, face):
        face_tensor = self.normalize_image(face)
        face_tensor = face_tensor.to(self.device)
        with torch.no_grad():
            embedding = self.resnet(face_tensor)
            if embedding.ndim == 0:
                embedding = embedding.unsqueeze(0)
            elif embedding.ndim == 1:
                embedding = embedding.unsqueeze(0)
            embedding = self.normalize_embedding(embedding)
        return embedding

