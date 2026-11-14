"""
Yield estimation module.
Inputs: crop, land area (acres), normal yield per acre.
Output: estimated yield loss %, expected remaining yield, assumptions, and formula.
"""

DEFAULT_YIELDS_PER_ACRE = {
    "Tomato": 150.0,
    "Potato": 100.0,
    "Corn": 25.0,
    "Apple": 80.0,
    "Grape": 90.0,
    "Pepper": 60.0,
    "Strawberry": 40.0,
    "Cherry": 30.0,
    "Blueberry": 25.0,
    "Orange": 100.0,
    "Peach": 70.0,
    "Soybean": 12.0,
    "Squash": 80.0,
}

def extract_crop_name(label: str | None) -> str:
    if not label:
        return "Crop"
    raw = label.split("___")[0].replace("_(maize)", "").replace(",_bell", "").replace("_(including_sour)", "").strip()
    return raw if raw else "Crop"

def estimate_yield_loss(
    crop: str | None,
    land_area_acres: float = 1.0,
    normal_yield_per_acre: float | None = None,
    disease_label: str | None = None,
    severity_level: str = "Low",
    severity_pct: float = 0.0,
    weather_risk: str = "Low"
) -> dict:
    crop_name = crop or extract_crop_name(disease_label)
    norm_yield = normal_yield_per_acre
    if norm_yield is None or norm_yield <= 0:
        norm_yield = DEFAULT_YIELDS_PER_ACRE.get(crop_name, 50.0)

    area = max(0.01, float(land_area_acres))
    total_normal = round(area * norm_yield, 2)

    is_healthy = disease_label and "healthy" in disease_label.lower()
    if is_healthy or severity_level == "None" or severity_pct <= 0:
        return {
            "crop": crop_name,
            "land_area_acres": area,
            "normal_yield_per_acre": norm_yield,
            "unit": "quintals",
            "total_normal_yield": total_normal,
            "estimated_loss_pct": 0.0,
            "estimated_loss_yield": 0.0,
            "expected_remaining_yield": total_normal,
            "severity_level": "None",
            "severity_pct": 0.0,
            "formula": "Estimated Yield Loss % = 0% (Plant is healthy)",
            "assumptions": [
                f"Standard benchmark yield for {crop_name}: {norm_yield} quintals/acre.",
                "Leaf tissue shows no significant lesions.",
                "Optimal photosynthetic area is retained."
            ],
            "disclaimer": "This is an empirical estimation for guidance only. Actual harvest varies with soil fertility, microclimate, and field management."
        }

    # 1. Base loss from severity %
    if severity_pct <= 10.0:
        base_loss = max(3.0, severity_pct * 1.0)
    elif severity_pct <= 30.0:
        base_loss = 10.0 + (severity_pct - 10.0) * 1.1
    else:
        base_loss = 32.0 + (severity_pct - 30.0) * 0.75
    base_loss = min(base_loss, 75.0)

    # 2. Disease virulence factor
    d_lower = (disease_label or "").lower()
    if any(x in d_lower for x in ["late_blight", "bacterial", "virus", "curl", "black_rot"]):
        disease_factor = 1.25
        disease_desc = "High virulence / systemic risk (1.25x)"
    elif any(x in d_lower for x in ["mildew", "scorch", "spot", "rust"]):
        disease_factor = 1.0
        disease_desc = "Moderate foliar impact (1.00x)"
    else:
        disease_factor = 1.1
        disease_desc = "Standard foliar impact (1.10x)"

    # 3. Weather risk multiplier
    w_lower = (weather_risk or "").lower()
    if "high" in w_lower:
        weather_factor = 1.15
        weather_desc = "High environmental favorability for pathogen spread (1.15x)"
    elif "medium" in w_lower:
        weather_factor = 1.05
        weather_desc = "Moderate weather risk (1.05x)"
    else:
        weather_factor = 1.0
        weather_desc = "Low or normal weather risk (1.00x)"

    # Calculate final loss %
    final_loss_pct = round(min(90.0, base_loss * disease_factor * weather_factor), 1)
    loss_yield = round(total_normal * (final_loss_pct / 100.0), 2)
    remaining_yield = round(max(0.0, total_normal - loss_yield), 2)

    return {
        "crop": crop_name,
        "land_area_acres": area,
        "normal_yield_per_acre": norm_yield,
        "unit": "quintals",
        "total_normal_yield": total_normal,
        "estimated_loss_pct": final_loss_pct,
        "estimated_loss_yield": loss_yield,
        "expected_remaining_yield": remaining_yield,
        "severity_level": severity_level,
        "severity_pct": severity_pct,
        "formula": "Estimated Yield Loss % = min(90%, Base Severity Loss % × Disease Factor × Weather Multiplier)",
        "assumptions": [
            f"Expected normal yield for {crop_name}: {norm_yield} quintals/acre across {area} acre(s) = {total_normal} quintals.",
            f"Base loss calculated from {severity_pct}% infected leaf area ({severity_level} level): {round(base_loss, 1)}%.",
            f"Pathogen virulence multiplier: {disease_desc}.",
            f"Weather risk multiplier: {weather_desc}.",
            f"Expected Remaining Yield = {total_normal} - {loss_yield} = {remaining_yield} quintals."
        ],
        "disclaimer": "This is an empirical agronomic estimate for risk assessment and planning. Actual yields depend on soil conditions, variety, fertilization, irrigation, and treatment."
    }
