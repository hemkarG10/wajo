from datetime import datetime

from scipy import stats


def calculate_lcb(alpha: float, beta_param: float, confidence: float = 0.95) -> float:
    """
    Returns the lower confidence bound of the Beta(alpha, beta) distribution.
    For a 95% one-sided bound, we want the point where the CDF is 0.05.
    """
    # 1 - confidence = 0.05 for 95% LCB
    return stats.beta.ppf(1.0 - confidence, alpha, beta_param)

def apply_decay(alpha: float, beta_param: float, last_update: datetime, now: datetime, half_life_days: float) -> tuple[float, float]:
    """
    Decays the evidence (alpha and beta) towards the prior (1, 1) based on elapsed time.
    """
    days = (now - last_update).total_seconds() / 86400.0
    if days <= 0 or half_life_days <= 0:
        return alpha, beta_param
        
    decay_factor = 0.5 ** (days / half_life_days)
    
    # We decay the evidence (alpha - 1) and (beta_param - 1)
    new_alpha = 1.0 + (alpha - 1.0) * decay_factor
    new_beta = 1.0 + (beta_param - 1.0) * decay_factor
    
    return new_alpha, new_beta
