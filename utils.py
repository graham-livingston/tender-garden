import math
if __name__ == '__main__':
    # Convert diameter and height from centimeters to meters for the formula
    diameter_cm = 1.87
    height_m = 87 / 100.0

    # Calculate D^2 * H
    d2h = (diameter_cm ** 2) * height_m
    print(f'd2h: {d2h}')

    # Calculate ln(Vol)
    ln_vol = -9.85 + 0.86 * math.log(d2h)

    # Calculate Volume
    volume = math.exp(ln_vol)

    # Calculate Bio Mass (CC)
    dry_biomass = 304 * volume
    
    # Calculate Carbon Content (CC)

    carbon_content = dry_biomass * 0.47
    
    # Calculate CO2 Equivalent (CO2-Eq)
    co2_equivalent = 3.67 * carbon_content


    print(f'biomass: {dry_biomass}')
