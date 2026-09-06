import numpy as np


def calculate_brier_score(predictions, outcomes):
    """
    Calculate Brier score.
    predictions: list of floats (0 to 1) representing confidence.
    outcomes: list of 0s and 1s representing actual outcomes (e.g. 1 if executed safely, 0 if violated).
    """
    if not predictions:
        return 0.0
    preds = np.array(predictions)
    outs = np.array(outcomes)
    return float(np.mean((preds - outs) ** 2))

def calculate_ece(predictions, outcomes, n_bins=10):
    """
    Calculate Expected Calibration Error (ECE) and data for Reliability Diagram.
    """
    if not predictions:
        return 0.0, []
        
    preds = np.array(predictions)
    outs = np.array(outcomes)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    reliability_data = []
    
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (preds > bin_lower) & (preds <= bin_upper)
        prop_in_bin = float(np.mean(in_bin))
        
        if prop_in_bin > 0:
            accuracy_in_bin = float(np.mean(outs[in_bin]))
            avg_confidence_in_bin = float(np.mean(preds[in_bin]))
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
            
            reliability_data.append({
                "bin": f"{bin_lower:.1f}-{bin_upper:.1f}",
                "accuracy": accuracy_in_bin,
                "confidence": avg_confidence_in_bin,
                "count": int(np.sum(in_bin))
            })
            
    return float(ece), reliability_data

def calculate_confusion_matrix(predictions, truths, labels):
    """
    Returns a 2D array (list of lists) representing the confusion matrix.
    labels: list of ordered categories (e.g., ["AUTO", "AUTO_NOTIFY", "ASK", "ESCALATE"])
    """
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
    
    for p, t in zip(predictions, truths):
        if p in label_to_idx and t in label_to_idx:
            matrix[label_to_idx[t]][label_to_idx[p]] += 1
            
    return matrix.tolist()
