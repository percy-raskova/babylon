"""Unequal Exchange formulas.

The mathematical basis for understanding global exploitation:
- Exchange Ratio: epsilon = (Lp/Lc) * (Wc/Wp)
- Exploitation Rate: percentage of value extracted
- Value Transfer: production * (1 - 1/epsilon)
- Prebisch-Singer Effect: terms of trade decline
"""


def calculate_exchange_ratio(
    periphery_labor_hours: float,
    core_labor_hours: float,
    core_wage: float,
    periphery_wage: float,
) -> float:
    """Calculate exchange ratio: epsilon = (Lp/Lc) * (Wc/Wp).

    The exchange ratio quantifies unequal exchange.
    When epsilon > 1, the periphery gives more value than it receives.

    Args:
        periphery_labor_hours: Labor hours in periphery
        core_labor_hours: Labor hours in core for same product
        core_wage: Core wage rate
        periphery_wage: Periphery wage rate

    Returns:
        Exchange ratio

    Raises:
        ValueError: If any denominator value is zero or negative

    Examples:
        >>> calculate_exchange_ratio(100.0, 100.0, 20.0, 5.0)  # Equal labor, 4x wage gap
        4.0
        >>> calculate_exchange_ratio(200.0, 100.0, 20.0, 10.0)  # 2x labor, 2x wage
        4.0
        >>> calculate_exchange_ratio(100.0, 100.0, 10.0, 10.0)  # Fair exchange
        1.0
    """
    if core_labor_hours <= 0:
        raise ValueError("core_labor_hours must be > 0")
    if periphery_wage <= 0:
        raise ValueError("periphery_wage must be > 0")

    labor_ratio = periphery_labor_hours / core_labor_hours
    wage_ratio = core_wage / periphery_wage

    return labor_ratio * wage_ratio


def calculate_exploitation_rate(exchange_ratio: float) -> float:
    """Convert exchange ratio to exploitation rate percentage.

    epsilon = 2 means 100% exploitation (double value extracted).
    epsilon = 1 means 0% exploitation (fair exchange).

    Args:
        exchange_ratio: The exchange ratio epsilon

    Returns:
        Exploitation rate as a percentage
    """
    return (exchange_ratio - 1) * 100


def calculate_value_transfer(
    production_value: float,
    exchange_ratio: float,
) -> float:
    """Calculate value transferred from periphery to core.

    Value transfer = production * (1 - 1/epsilon)

    Args:
        production_value: Value of peripheral production
        exchange_ratio: The exchange ratio epsilon

    Returns:
        Value transferred to core
    """
    if exchange_ratio <= 0:
        return 0.0

    transfer_fraction = 1 - (1 / exchange_ratio)
    return production_value * transfer_fraction


def prebisch_singer_effect(
    initial_price: float,
    production_increase: float,
    elasticity: float,
) -> float:
    """Calculate Prebisch-Singer effect on commodity prices.

    Terms of trade decline for commodity exporters:
    More production -> lower prices -> same poverty.

    Args:
        initial_price: Initial commodity price
        production_increase: Fractional increase in production (0.2 = 20%)
        elasticity: Price elasticity of demand (typically negative)

    Returns:
        New price after production increase
    """
    # Price change = elasticity * production change
    # (simplified model of supply-demand dynamics)
    price_change_fraction = elasticity * production_increase
    new_price = initial_price * (1 + price_change_fraction)

    return max(0.0, new_price)
