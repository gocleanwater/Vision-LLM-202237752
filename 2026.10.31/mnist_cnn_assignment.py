"""MNIST CNN 학습, 평가 그래프, 학습된 Feature Map 시각화 과제."""

import random
import time

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


SEED = 42
DATA_ROOT = "../src/datasets"
MODEL_PATH = "../src/models/MNIST/MNIST_CNN.pth"

BATCH_SIZE = 64
TEST_BATCH_SIZE = 1000
EPOCHS = 3
LEARNING_RATE = 0.001
NUM_WORKERS = 0


class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=8,
            kernel_size=3,
            stride=1,
            padding=1,
        )
        self.conv2 = nn.Conv2d(
            in_channels=8,
            out_channels=16,
            kernel_size=3,
            stride=1,
            padding=1,
        )
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(16 * 7 * 7, 64)
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x, return_features=False):
        conv1_output = self.conv1(x)
        relu1_output = F.relu(conv1_output)
        pool1_output = self.pool(relu1_output)
        conv2_output = self.conv2(pool1_output)
        relu2_output = F.relu(conv2_output)
        pool2_output = self.pool(relu2_output)
        flattened = torch.flatten(pool2_output, start_dim=1)
        fc1_output = F.relu(self.fc1(flattened))
        logits = self.fc2(fc1_output)

        if return_features:
            features = {
                "conv1": conv1_output,
                "relu1": relu1_output,
                "pool1": pool1_output,
                "conv2": conv2_output,
                "relu2": relu2_output,
                "pool2": pool2_output,
            }
            return logits, features

        return logits


def train_one_epoch(model, data_loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    correct_count = 0
    sample_count = 0

    for images, labels in data_loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        batch_size = images.size(0)
        total_loss += loss.item() * batch_size
        predictions = logits.argmax(dim=1)
        correct_count += (predictions == labels).sum().item()
        sample_count += batch_size

    average_loss = total_loss / sample_count
    accuracy = correct_count / sample_count
    return average_loss, accuracy


def evaluate(model, data_loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct_count = 0
    sample_count = 0

    with torch.no_grad():
        for images, labels in data_loader:
            images = images.to(device)
            labels = labels.to(device)

            logits = model(images)
            loss = criterion(logits, labels)

            batch_size = images.size(0)
            total_loss += loss.item() * batch_size
            predictions = logits.argmax(dim=1)
            correct_count += (predictions == labels).sum().item()
            sample_count += batch_size

    average_loss = total_loss / sample_count
    accuracy = correct_count / sample_count
    return average_loss, accuracy


def show_feature_maps(feature_tensor, title, max_maps=8, cmap="gray"):
    feature_maps = feature_tensor[0].detach().cpu()
    channel_count = min(feature_maps.shape[0], max_maps)
    column_count = 4
    row_count = int(np.ceil(channel_count / column_count))
    figure = plt.figure(figsize=(12, 3 * row_count))

    for channel_index in range(channel_count):
        axis = figure.add_subplot(row_count, column_count, channel_index + 1)
        axis.imshow(feature_maps[channel_index], cmap=cmap)
        axis.set_title(f"Channel {channel_index}")
        axis.axis("off")

    figure.suptitle(title)
    figure.tight_layout()
    return figure


def plot_training_history(
    train_loss_history,
    test_loss_history,
    train_accuracy_history,
    test_accuracy_history,
):
    epoch_axis = range(1, len(train_loss_history) + 1)

    # TODO: plt.plot(x축_데이터, y축_데이터, marker="o", label="데이터_이름")을 사용하여 그래프 생성
    loss_figure, loss_axis = plt.subplots(figsize=(8, 5))
    # TODO: train_loss_history 그래프 생성
    loss_axis.plot(
        epoch_axis,
        train_loss_history,
        marker="o",
        label="Train Loss",
    )
    # TODO: test_loss_history 그래프 생성
    loss_axis.plot(
        epoch_axis,
        test_loss_history,
        marker="o",
        label="Test Loss",
    )
    loss_axis.set_xlabel("Epoch")
    loss_axis.set_ylabel("Loss")
    loss_axis.set_title("CNN Loss")
    loss_axis.grid()
    loss_axis.legend()
    loss_figure.tight_layout()

    train_accuracy_percent = [accuracy * 100 for accuracy in train_accuracy_history]
    test_accuracy_percent = [accuracy * 100 for accuracy in test_accuracy_history]

    # TODO: plt.plot(x축_데이터, y축_데이터, marker="o", label="데이터_이름")을 사용하여 그래프 생성
    accuracy_figure, accuracy_axis = plt.subplots(figsize=(8, 5))
    # TODO: train_accuracy_history 그래프 생성 (백분율)
    accuracy_axis.plot(
        epoch_axis,
        train_accuracy_percent,
        marker="o",
        label="Train Accuracy",
    )
    # TODO: test_accuracy_history 그래프 생성 (백분율)
    accuracy_axis.plot(
        epoch_axis,
        test_accuracy_percent,
        marker="o",
        label="Test Accuracy",
    )
    accuracy_axis.set_xlabel("Epoch")
    accuracy_axis.set_ylabel("Accuracy (%)")
    accuracy_axis.set_title("CNN Accuracy")
    accuracy_axis.grid()
    accuracy_axis.legend()
    accuracy_figure.tight_layout()

    return loss_figure, accuracy_figure


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    transform = transforms.ToTensor()
    train_dataset = datasets.MNIST(
        root=DATA_ROOT,
        train=True,
        transform=transform,
        download=True,
    )
    test_dataset = datasets.MNIST(
        root=DATA_ROOT,
        train=False,
        transform=transform,
        download=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=TEST_BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
    )

    device = torch.device("cpu")
    model = SimpleCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    train_loss_history = []
    train_accuracy_history = []
    test_loss_history = []
    test_accuracy_history = []

    training_start_time = time.perf_counter()

    for epoch in range(EPOCHS):
        epoch_start_time = time.perf_counter()
        train_loss, train_accuracy = train_one_epoch(
            model,
            train_loader,
            criterion,
            optimizer,
            device,
        )
        test_loss, test_accuracy = evaluate(
            model,
            test_loader,
            criterion,
            device,
        )

        train_loss_history.append(train_loss)
        train_accuracy_history.append(train_accuracy)
        test_loss_history.append(test_loss)
        test_accuracy_history.append(test_accuracy)

        epoch_time = time.perf_counter() - epoch_start_time
        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Train loss: {train_loss:.4f} | "
            f"Train accuracy: {train_accuracy * 100:.2f}% | "
            f"Test loss: {test_loss:.4f} | "
            f"Test accuracy: {test_accuracy * 100:.2f}% | "
            f"Time: {epoch_time:.2f}s"
        )

    total_training_time = time.perf_counter() - training_start_time
    print(f"Total CPU training time: {total_training_time:.2f}s")

    plot_training_history(
        train_loss_history,
        test_loss_history,
        train_accuracy_history,
        test_accuracy_history,
    )

    # TODO: CNN 각 층의 Feature Map 시각화
    # TODO: cmap="viridis" 사용


    # TODO: 이미지 선택
    image, true_label = test_dataset[0]
    input_image = image.unsqueeze(0).to(device) # Batch 차원이 없기 때문에 추가를 위해 `unsqueeze(0)`이 필요.
    # [C,H,W] → [1,C,H,W]
    #  이미지       CNN

    # TODO: 역전파(파라미터 수정) 없이 순전파 수행
    model.eval()
    with torch.no_grad():
        logits, features = model(input_image, return_features=True)

    predicted_label = logits.argmax(dim=1).item()
    print(f"True label: {true_label}")
    print(f"Predicted label: {predicted_label}")

    # TODO: Conv1 Feature Maps 8개 시각화
    show_feature_maps(
        features["conv1"],
        title="Conv1 Feature Maps",
        max_maps=8,
        cmap="viridis",
    )
    # TODO: Conv2 Feature Maps 16개 시각화
    show_feature_maps(
        features["conv2"],
        title="Conv2 Feature Maps",
        max_maps=16,
        cmap="viridis",
    )

    # TODO: 6개 Layer별 대표 Feature Map 4개씩 비교
    layer_names = ["conv1", "relu1", "pool1", "conv2", "relu2", "pool2"]
    for layer_name in layer_names:
        show_feature_maps(
            features[layer_name],
            title=f"{layer_name} Feature Maps",
            max_maps=4,
            cmap="viridis",
        )

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved: {MODEL_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
