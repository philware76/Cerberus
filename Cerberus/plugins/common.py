
# Product ID to Product Plugin Name mapping.
import logging

PROD_ID_MAPPING = {
    "K": "Tactical_A_Controller",
    "I": "Tactical_G_Controller",
    "B": "Tactical_U_Transceiver",
    "A": "Tactical_G_Transceiver"
}

# Nesie types according to EthDiscovery response
NESIE_TYPES = {
    'A': 'Tac_G_TRX',
    'I': 'Tac_G_Controller',
    'B': 'Tac_A_TRX/Tac_U',
    'K': 'Tac_A_Controller',
    'T': 'nesie2_pa_tx',
    'C': 'nesie2_controller',
    'U': 'Covert',    # C/U-NESIE
    'R': 'REDSTREAK',
    'F': 'flight_unit',
    'G': 'GAN',
    '': 'Other'
}


def getSettledReading(readValueFunc, minSamples=10, maxSamples=100):
    """Return a stable measurement using 99% confidence interval on the mean.

        Strategy:
          - Collect batches of readings (min_batch) from readValueFunc()
          - After each batch, compute sample mean (m), sample standard deviation (s, ddof=1).
          - 99% CI half-width = z * s / sqrt(n) with z≈2.576.
          - Stop when half-width <= tolerance (abs or relative) OR max_samples reached.
        """
    import numpy as np

    z = 2.576  # 99% two-sided z-score
    tolerance_abs = 0.05  # dB absolute half-width target
    tolerance_rel = 0.002  # 0.2% of mean as alternative stopping criterion

    readings: list[float] = []
    while True:
        # acquire a batch
        for _ in range(minSamples):
            readings.append(readValueFunc())
            if len(readings) >= maxSamples:
                break

        n = len(readings)
        if n < 2:
            continue

        arr = np.array(readings, dtype=float)
        mean = float(arr.mean())
        # sample std (ddof=1) guard small n
        std = float(arr.std(ddof=1))
        half_width = z * std / (n ** 0.5)
        rel_hw = half_width / abs(mean) if mean != 0 else float('inf')

        logging.debug(f"SettledMeas n={n} mean={mean:.3f} std={std:.3f} hw99={half_width:.3f} rel={rel_hw:.4f}")

        if (half_width <= tolerance_abs) or (rel_hw <= tolerance_rel) or n >= maxSamples:
            return mean
