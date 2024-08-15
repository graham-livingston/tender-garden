def calculate_tree_weight_cm(D_cm, H_cm, r=0.725):
    """
    Calculate various weights related to a tree based on its diameter (D) in centimeters and height (H) in centimeters.
    
    :param D_cm: Diameter of the tree trunk in centimeters
    :param H_cm: Height of the tree in centimeters
    :param r: Proportion of dry mass to green mass, default is 72.5%
    :return: A dictionary containing TGW (Total Green Weight), DW (Dry Weight), CW (Carbon Weight), and CO2 sequestered in kilograms.
    """
    
    # Conversion factors
    cm_to_inches = 0.393701
    cm_to_feet = 0.0328084
    pounds_to_kg = 0.453592
    
    # Convert diameter and height from centimeters to inches and feet respectively
    D = D_cm * cm_to_inches
    H = H_cm * cm_to_feet
    
    # Determine TGW (Total Green Weight) in pounds
    if D < 11:
        TGW_pounds = 0.3 * (D ** 2) * H
    else:
        TGW_pounds = 0.18 * (D ** 2) * H
    
    # Convert TGW to kilograms
    TGW_kg = TGW_pounds * pounds_to_kg
    
    # Calculate DW (Dry Weight) in kilograms
    DW_kg = r * TGW_kg
    
    # Calculate CW (Carbon Weight) in kilograms
    CW_kg = 0.5 * DW_kg
    
    # Calculate CO2 sequestered in kilograms
    CO2_kg = 3.6663 * CW_kg
    
    # Return the results as a dictionary
    return {
        "Total Green Weight (TGW)": TGW_kg,
        "Dry Weight (DW)": DW_kg,
        "Carbon Weight (CW)": CW_kg,
        "CO2 Sequestered": CO2_kg
    }
