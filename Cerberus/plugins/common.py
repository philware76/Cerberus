
# Product ID to Product Plugin Name mapping.
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
