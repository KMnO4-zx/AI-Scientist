import os
import json
import numpy as np
import matplotlib.pyplot as plt

def load_results(run_dir):
    with open(os.path.join(run_dir, "final_info.json"), "r") as f:
        return json.load(f)

def plot_results(results, labels):
    for operation, data in results.items():
        means = data["means"]
        steps = list(range(len(means["final_train_loss_mean"])))
        
        plt.figure(figsize=(10, 5))
        
        # Plot training and validation loss
        plt.subplot(1, 2, 1)
        plt.plot(steps, means["final_train_loss_mean"], label="Train Loss")
        plt.plot(steps, means["final_val_loss_mean"], label="Val Loss")
        plt.title(f"{operation} Loss")
        plt.xlabel("Steps")
        plt.ylabel("Loss")
        plt.legend()
        
        # Plot training and validation accuracy
        plt.subplot(1, 2, 2)
        plt.plot(steps, means["final_train_acc_mean"], label="Train Acc")
        plt.plot(steps, means["final_val_acc_mean"], label="Val Acc")
        plt.title(f"{operation} Accuracy")
        plt.xlabel("Steps")
        plt.ylabel("Accuracy")
        plt.legend()
        
        plt.suptitle(labels[operation])
        plt.tight_layout()
        plt.show()
        plt.savefig(f"./{operation}.png")

if __name__ == "__main__":
    labels = {
        "x_div_y": "Modular Division",
        "x_minus_y": "Modular Subtraction",
        "x_plus_y": "Modular Addition",
        "permutation": "Permutation",
    }
    
    results = {}
    for run in labels.keys():
        run_dir = f"run_{run}"
        if os.path.exists(run_dir):
            results[run] = load_results(run_dir)
    
    plot_results(results, labels)
