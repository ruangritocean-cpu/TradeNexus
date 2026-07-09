import itertools
import random
from typing import Dict, Any, List, Tuple

DEFAULT_PARAM_RANGES = {
    "confluence_threshold": [70.0],
    "rr_threshold": [1.5],
    "adx_threshold": [25.0],
    "squeeze_block_enabled": [True],
    "sideways_block_enabled": [True],
    "min_regime_score": [60.0],
    "allow_counter_trend_scalp": [True],
    "max_bars_to_hold": [24],
    "atr_buffer_multiple": [1.5],
    "volume_confirmation_weight": [1.0],
    "smc_weight": [1.0]
}

def generate_parameter_grid(
    ranges: Dict[str, List[Any]] = None,
    max_combinations: int = 100,
    sampling_seed: int = 42
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generates combinations of parameters from ranges.
    Enforces max_combinations safety limits by sampling deterministically if needed.
    """
    if ranges is None:
        ranges = DEFAULT_PARAM_RANGES
        
    # Standardize all parameters to list formats, fallback to default single values if missing
    full_ranges = {}
    for key, default_val in DEFAULT_PARAM_RANGES.items():
        if key in ranges and isinstance(ranges[key], list) and len(ranges[key]) > 0:
            full_ranges[key] = ranges[key]
        else:
            full_ranges[key] = default_val
            
    # Generate all combination product tuples
    keys = list(full_ranges.keys())
    values = [full_ranges[k] for k in keys]
    
    product_tuples = list(itertools.product(*values))
    total_combos = len(product_tuples)
    
    # Deterministic sampling or truncation
    if total_combos > max_combinations:
        # We want this to be reproducible
        rng = random.Random(sampling_seed)
        sampled_tuples = rng.sample(product_tuples, max_combinations)
        sampling_method = "DETERMINISTIC_SAMPLE"
    else:
        sampled_tuples = product_tuples
        sampling_method = "BRUTE_FORCE"
        
    # Convert tuples back to dictionary lists
    combos = []
    for t in sampled_tuples:
        combos.append(dict(zip(keys, t)))
        
    metadata = {
        "grid_total_combinations": total_combos,
        "grid_evaluated_combinations": len(combos),
        "grid_sampling_method": sampling_method,
        "sampling_seed": sampling_seed
    }
    
    return combos, metadata
